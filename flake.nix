{
  description = "ani-cursor-tool: Convert Windows .ani/.cur files to a KDE cursor theme";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        devShells.default = pkgs.mkShell {
          packages = [ pkgs.python3 pkgs.win2xcur ];
        };

        packages.default = pkgs.writeShellApplication {
          name = "ani-cursor-tool";
          runtimeInputs = [ pkgs.python3 pkgs.win2xcur ];
          text = ''
            exec python3 ${./src/main.py} "$@"
          '';
        };
      });
}
