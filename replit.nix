{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.cmake
    pkgs.ninja
    pkgs.gcc
    pkgs.openssl
    pkgs.liboqs          # ML-DSA-65 + ML-KEM-768 (NIST PQC 2024)
    pkgs.curl
    pkgs.git
  ];
}
