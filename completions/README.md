# Shell completions

Completions for **rfcman** — a BigTalk utility.

Install after `pip install rfcman`:

```bash
rfcman --install-completion bash
rfcman --install-completion zsh
rfcman --install-completion fish
```

Or source a checked-in script:

```bash
# bash
source completions/rfcman.bash

# zsh
source completions/rfcman.zsh

# fish
source completions/rfcman.fish
```

Regenerate after CLI changes:

```bash
rfcman --show-completion bash > completions/rfcman.bash
rfcman --show-completion zsh > completions/rfcman.zsh
rfcman --show-completion fish > completions/rfcman.fish
```
