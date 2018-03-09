import inspect
import shlex

from collections import OrderedDict


def _collect_handlers(module):
    result = []
    for name in dir(module):
        if name.startswith('_'):
            continue
        obj = getattr(module, name)
        if inspect.iscoroutinefunction(obj):
            result.append(obj)
    return result


def generate_commands(module):
    result = {}
    for handler in _collect_handlers(module):
        cmd_name, cmd_desc = (i.strip() for i in handler.__doc__.split('-', 1))
        cmd_args = []
        handler_params = OrderedDict(inspect.signature(handler).parameters)
        requires_sa = bool(handler_params.pop('sa_conn', None))
        for idx, item in enumerate(handler_params.items()):
            k, p = item
            cmd_args.append((idx, k, p.empty is p.default))
        result[cmd_name] = {
            'handler': handler,
            'args': cmd_args,
            'desc': cmd_desc,
            'requires_sa': requires_sa
        }
    return result


def generate_help(commands, *, completion=False):
    parts = []
    if not completion:
        parts.append('/start alias for /help')
        parts.append('/help show this message')
    for name, data in sorted(commands.items(), key=lambda x: x[0]):
        args = []
        for _, arg_name, arg_required in data['args']:
            if arg_required:
                args.append('<{}>'.format(arg_name))
            else:
                args.append('[{}]'.format(arg_name))
        args = ' '.join(args)
        if completion:
            parts.append('{} - {}{}'.format(
                name,
                data['desc'],
                ': {}'.format(args) if args else ''
            ))
        else:
            name = '/{}'.format(name)
            parts.append(' '.join(i for i in (name, args, data['desc']) if i))
    return '\n'.join(parts)


class CommandHandler:
    def __init__(self, commands, sa_engine):
        self.commands = commands
        self.sa_engine = sa_engine
        self.help_message = generate_help(commands)
        self.completion_message = generate_help(commands, completion=True)

    async def handle(self, raw_command):
        try:
            parts = shlex.split(raw_command)
        except ValueError as exc:
            return str(exc)

        if not parts:
            return 'Empty command'

        name, raw_args = parts[0][1:], parts[1:]

        if name in ('start', 'help'):
            return 'Too many arguments' if raw_args else self.help_message

        if name == 'listcommands':
            return 'Too many arguments' if raw_args else self.completion_message

        command = self.commands.get(name)
        if not command:
            return 'Command not found'

        if len(raw_args) > len(command['args']):
            return 'Too many arguments'

        args = {}
        for arg_idx, arg_name, arg_required in command['args']:
            try:
                arg_value = raw_args[arg_idx]
            except IndexError:
                if arg_required:
                    return '%s is required' % arg_name
                arg_value = None
            args[arg_name] = arg_value

        handler = command['handler']

        if command['requires_sa']:
            async with self.sa_engine.acquire() as sa_conn:
                args['sa_conn'] = sa_conn
                return await handler(**args)

        return await handler(**args)
