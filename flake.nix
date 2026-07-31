{
  description = "ARTCB Blockchain Node — environnement Nix reproductible";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pkgs.gcc
            pkgs.cmake
            pkgs.gnumake
            pkgs.openssl
            pkgs.nodejs_22
            pkgs.curl
            pkgs.git
          ];

          shellHook = ''
            echo "🔗 ARTCB devenv Nix"
            export PYTHONPATH="$PWD:$PYTHONPATH"
            export ARTCB_DEBUG=true
            export ARTCB_DATA_DIR="$PWD/data"

            if [ ! -d ".venv" ]; then
              echo "📦 Installation des dépendances Python..."
              python -m venv .venv
              .venv/bin/pip install -r requirements.txt --quiet
            fi
            source .venv/bin/activate
            echo "✅ Prêt — lancer : make api"
          '';
        };
      });
}
