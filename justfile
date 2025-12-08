nixos-build:
    #!/usr/bin/env bash
    target=x86_64-linux-gnu
    interpreter=/lib64/ld-linux-x86-64.so.2
    name="telefeed-$(cargo read-manifest | jq -r '.version')_$target"
    build_dir=data/build
    build_path=$build_dir/$name
    echo $build_path
    cargo build --release
    mkdir -p $build_dir
    cp target/release/telefeed $build_path
    patchelf --set-interpreter $interpreter $build_path
    echo $build_path
run:
    cargo run -- data/config.toml
format:
    nixfmt flake.nix
    cargo fmt
lint:
    cargo clippy --all-targets --all-features -- -D warnings
test:
    cargo test
pre-commit: format lint test
