# This function returns a attrset of `devenv` modules
# which can be passed to `mkShell`.
{
  self,
  lib,
  pkgs,
  ...
}:
{
  python = [
    {
      packages = [
        # Language Server.
        pkgs.pyright

        # Formatter and linter.
        pkgs.ruff

        pkgs.stdenv.cc.cc.lib # fix: libstdc++ required by jupyter.
        pkgs.libz # fix: for numpy/pandas import
      ];

      env = {
        RUFF_CACHE_DIR = ".output/cache/ruff";
      };

      enterShell = ''
        just setup
      '';

      env.LD_LIBRARY_PATH = "${lib.makeLibraryPath [
        pkgs.stdenv.cc.cc.lib
        pkgs.libz
      ]}";
    }
  ];
}
