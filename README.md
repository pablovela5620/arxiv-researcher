<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" height="200px" srcset="https://raw.githubusercontent.com/pablovela5620/arxiv-researcher/main/assets/arxiv-researcher_TSP.png">
    <img alt="logo" height="200px" src="https://raw.githubusercontent.com/pablovela5620/arxiv-researcher/main/assets/arxiv-researcher_TSP.png">
  </picture>
</div>

# Arxiv Researcher
Built with Langchain, Nougat, OpenAI, Gradio, and Pixi
## Prerequisites
Only tested on a linux machine, requires a CUDA gpu as Nougat will be too slow otherwise
## Quick Start
### Step 1. Install pixi package manager

```sh
curl -fsSL https://pixi.sh/install.sh | bash
```
Make sure to restart your terminal or source your shell for changes to take affect

### Step 2. Set your OpenAI Key
```sh
export OPENAI_API_KEY=<your_key_here>
```

### Step 3. Run Gradio app with Pixi
```sh
pixi run app
```

## Todo 
- [x] Initial Release with OpenAI 3.5-16k
- [ ] Add CTransfomers/Ollama for local version
- [ ] Colab Demo
- [ ] Huggingface Spaces Demo 

## Acknowledgments

- [Yuvi for original demo inspriing to make this](https://twitter.com/yvrjsharma/status/1697632485440659516)
- [Nougat](https://github.com/facebookresearch/nougat)
- [Langchain](https://www.langchain.com/)
- [Gradio](http://gradio.dev/)
- [Pixi](pixi.sh)
- [OpenAI](https://openai.com/)
