{
  description = "Seattle traffic cameras — live SDOT camera viewer";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python3   # scripts/fetch_cameras.py, scripts/generate_html.py (stdlib only)
            curl      # fetch_cameras.py shells out to curl for HTTPS
          ];
        };
      });
}
