{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.gcc
    pkgs.cmake
    pkgs.gnumake
    pkgs.openssl
    pkgs.nodejs_22
    pkgs.curl
  ];
  env = {
    PYTHONPATH = "${pkgs.lib.placeholder "out"}";
  };
}
