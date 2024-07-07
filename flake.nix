{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    rust-overlay.url = "github:oxalica/rust-overlay";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs =
    inputs:
    inputs.flake-utils.lib.eachDefaultSystem (
      system:
      let
        overlays = [ inputs.rust-overlay.overlays.default ];
        pkgs = import inputs.nixpkgs { inherit system overlays; };
        openssl = pkgs.openssl;
        pkg-config = pkgs.pkg-config;
        redis = pkgs.redis;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            openssl
            pkg-config
            (pkgs.lib.hiPrio (
              pkgs.rust-bin.stable.latest.minimal.override {
                extensions = [
                  "rust-docs"
                  "clippy"
                ];
              }
            ))
            (pkgs.rust-bin.selectLatestNightlyWith (
              toolchain:
              toolchain.minimal.override {
                extensions = [
                  "rust-analyzer"
                  "rustfmt"
                ];
              }
            ))
            redis
          ];
          shellHook = ''
            export CARGO_HOME="$PWD/dev/data/cargo"
            export PATH="$CARGO_HOME/bin:$PATH"
            mkdir -p $CARGO_HOME
          '';
        };
      }
    );
}
