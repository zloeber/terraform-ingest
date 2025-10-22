# Development

I use [task](https://taskfile.dev) along with [mise](https://mise.jdx.dev) for everything locally. You can setup mise by running `./configure.sh` or just install the binaries used if you already have mise in your path via `mise install -y`

## Building

This project uses uv + hatch + hatch-vcs for building and automatic versioning. You can build the local docker image using `task build:image` if that's your thing. 