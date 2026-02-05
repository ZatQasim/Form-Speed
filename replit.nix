{ pkgs }: {
  deps = [
    pkgs.wireguard-tools
    pkgs.wireguard-go
    pkgs.iproute2
    pkgs.git
    pkgs.nano
  ];
}