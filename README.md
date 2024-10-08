# ollama-tk

[![](https://img.shields.io/pypi/v/ollama-tk?style=flat-square)](https://pypi.org/project/ollama-tk/)
[![](https://img.shields.io/github/actions/workflow/status/thegamecracks/ollama-tk/black-lint.yml?style=flat-square&label=black)](https://black.readthedocs.io/en/stable/)
[![](https://img.shields.io/github/actions/workflow/status/thegamecracks/ollama-tk/pyright-lint.yml?style=flat-square&label=pyright)](https://microsoft.github.io/pyright/#/)
[![](https://img.shields.io/github/actions/workflow/status/thegamecracks/ollama-tk/pytest.yml?style=flat-square&label=pytest)](https://docs.pytest.org/en/stable/)

A simple, tkinter-based GUI for chatting with an LLM via any [Ollama] API.

[Ollama]: https://github.com/ollama/ollama

![](https://raw.githubusercontent.com/thegamecracks/ollama-tk/main/docs/images/demo.gif)

You might also be interested in:
- [ollama-gui](https://github.com/chyok/ollama-gui):
  A similar PyPI project written by chyok. Turns out they beat me to the punch a few months earlier!
- [Open WebUI](https://github.com/open-webui/open-webui):
  A much more capable, locally hostable web dashboard for interacting with LLM
  APIs, including Ollama.

## Usage

1. With Python 3.11+ installed, run the following:

   ```sh
   pip install ollama-tk
   ```

   Or, if you want the development version and you have Git installed:

   ```sh
   pip install git+https://github.com/thegamecracks/ollama-tk
   ```

2. Then start the program with:

   ```sh
   ollama-tk
   # Or:
   python -m ollamatk
   ```

Clicking on any message will copy its contents to your clipboard.

## License

This project is written under the MIT license.

This application uses [Material Design Icons] which is licensed under
[Apache 2.0](https://github.com/google/material-design-icons/blob/master/LICENSE).

[Material Design Icons]: https://icon-sets.iconify.design/material-symbols/person/
