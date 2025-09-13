# 🐢 Code-Turtle: AI-Powered Code Reviews in GitHub Actions

Code-Turtle is a GitHub Action that provides automated AI-powered code reviews for your pull requests. It analyzes the code changes, offers suggestions, and posts the review as a comment, helping you catch potential issues and improve code quality effortlessly.

## ✨ Features

  * **Automated Code Reviews**: Get instant feedback on your pull requests.
  * **Marketplace Action**: Easily integrate into any public or private repository from the GitHub Marketplace.
  * **Customizable AI Models**: Use the default model or specify any GGUF-compatible model from sources like Hugging Face.
  * **Efficient Inference**: Powered by `llama.cpp` for fast and efficient code analysis.

-----

## ⚙️ How It Works

The magic happens through a streamlined GitHub Actions workflow:

1.  When a pull request is opened, reopened, or updated, your workflow is triggered.
2.  The workflow checks out the code and generates a `diff` of the changes.
3.  It then calls the `code-turtle` action, passing the pull request details.
4.  The action downloads the specified AI model, analyzes the `diff`, and generates a code review.
5.  Finally, the AI-generated review is posted as a comment on the pull request.

-----

## 🚀 How to Use Code-Turtle

Integrating Code-Turtle into your project is simple.

### 1\. Create a Workflow File

In your repository, create a new file in the `.github/workflows/` directory. You can name it `ai-review.yml`.

### 2\. Add the Workflow Code

Paste the following YAML code into your new workflow file. This single job will handle everything from checking out the code to posting the review.

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, reopened, synchronize]

jobs:
  ai-code-review:
    runs-on: ubuntu-latest
    permissions:
      # Required for the action to post comments on your PRs
      pull-requests: write
    steps:
      - name: 1. Checkout Repository
        uses: actions/checkout@v4
        with:
          # Fetch all history to ensure the diff is accurate
          fetch-depth: 0

      - name: 2. Generate Diff
        run: |
          git fetch origin ${{ github.event.pull_request.base.sha }}
          git fetch origin ${{ github.event.pull_request.head.sha }}
          git diff ${{ github.event.pull_request.base.sha }} ${{ github.event.pull_request.head.sha }} > code.diff

      - name: 3. Run Code-Turtle AI Review
        uses: richard-m-j/code-turtle@v1 # Make sure to use the latest version
        with:
          pr_number: ${{ github.event.pull_request.number }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          repository: ${{ github.repository }}
```

### 3\. That's It\!

Commit the new workflow file to your repository. The next time a pull request is opened or updated, Code-Turtle will automatically review the changes and post a comment.

-----

## 🎨 Customization: Using a Different AI Model

Code-Turtle uses `Meta-Llama-3-8B-Instruct` by default. You can easily switch to any other GGUF-compatible model from the [Hugging Face Hub](https://huggingface.co/models?search=gguf) by adding the `model_url` input.

Here is an example using the `Qwen2-7B-Instruct` model:

```yaml
      - name: 3. Run Code-Turtle AI Review
        uses: richard-m-j/code-turtle@v1
        with:
          pr_number: ${{ github.event.pull_request.number }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          repository: ${{ github.repository }}
          # Add the model_url input to specify a different model
          model_url: 'https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct-q5_k_m.gguf'
```

### Action Inputs

Here are all the available inputs for the action:

| Input | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `pr_number` | The number of the pull request to review. | `true` | `N/A` |
| `github_token` | The `GITHUB_TOKEN` secret. | `true` | `${{ secrets.GITHUB_TOKEN }}` |
| `repository` | The repository name (e.g., `owner/repo`). | `true` | `${{ github.repository }}` |
| `model_url` | The URL of the GGUF model to use for the review. | `false` | `https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/...` |