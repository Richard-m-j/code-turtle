# 🐢 Code-Turtle: AI-Powered Code Reviews in GitHub Actions

Code-Turtle is a GitHub Action that provides automated AI-powered code reviews for your pull requests. It analyzes the code changes, offers suggestions, and posts the review as a comment, helping you catch potential issues and improve code quality effortlessly.

## ✨ Features

  * **Automated Code Reviews**: Get instant feedback on your pull requests.
  * **Reusable Workflow**: Easily integrate into any public or private repository.
  * **Customizable AI Models**: Use the default model or specify any GGUF-compatible model from sources like Hugging Face.
  * **Efficient Inference**: Powered by `llama.cpp` for fast and efficient code analysis.

## ⚙️ How It Works

The magic happens through a reusable GitHub Actions workflow:

1.  When a pull request is opened, reopened, or updated, a "caller" workflow is triggered in your repository.
2.  This workflow generates a `diff` of the changes and uploads it as an artifact.
3.  It then calls the `code-turtle` reusable workflow.
4.  The reusable workflow downloads the specified AI model, analyzes the `diff`, and generates a code review.
5.  Finally, the AI-generated review is posted as a comment on the pull request.

## 🚀 How to Use Code-Turtle

Integrating Code-Turtle into your project is simple. Just follow these steps:

### 1\. Create a Workflow File

In your repository, create a new file in the `.github/workflows/` directory. For example, you can name it `ai-review.yml`.

### 2\. Add the Workflow Code

Paste the following YAML code into your new workflow file:

```yaml
name: Trigger AI Code Review

on:
  pull_request:
    types: [opened, reopened, synchronize]

jobs:
  # This job generates the diff of the pull request
  generate-diff:
    runs-on: ubuntu-latest
    steps:
      - name: 1. Checkout repository
        uses: actions/checkout@v4
        with:
          # Fetch all history to ensure the diff is accurate
          fetch-depth: 0

      - name: 2. Generate and Upload Diff as Artifact
        run: |
          git fetch origin ${{ github.event.pull_request.base.sha }}
          git fetch origin ${{ github.event.pull_request.head.sha }}
          git diff ${{ github.event.pull_request.base.sha }} ${{ github.event.pull_request.head.sha }} > code.diff
      - uses: actions/upload-artifact@v4
        with:
          name: code-diff-artifact
          path: code.diff

  # This job calls the reusable Code-Turtle workflow
  trigger-review:
    # This job depends on the diff being generated first
    needs: generate-diff
    # Use the Code-Turtle reusable workflow from the main branch
    uses: richard-m-j/code-turtle/.github/workflows/reusable-review.yml@main
    permissions:
      # Required to allow the action to write comments on pull requests
      pull-requests: write
    with:
      # Pass the pull request number to the reusable workflow
      pr_number: ${{ github.event.pull_request.number }}
    # Inherit secrets, which includes the default GITHUB_TOKEN
    secrets: inherit
```

### 3\. That's It\!

Commit the new workflow file to your repository. The next time a pull request is opened or updated, Code-Turtle will automatically review the changes and post a comment.

## 🎨 Customization: Using a Different AI Model

Code-Turtle uses `Meta-Llama-3-8B-Instruct` by default. However, you can easily switch to any other GGUF-compatible model.

To use a custom model, simply add the `model_url` input to your `trigger-review` job. You can find many GGUF models on the [Hugging Face Hub](https://huggingface.co/models?search=gguf).

Here is an example using the `phi-2` model:

```yaml
  trigger-review:
    needs: generate-diff
    uses: richard-m-j/code-turtle/.github/workflows/reusable-review.yml@main
    permissions:
      pull-requests: write
    with:
      pr_number: ${{ github.event.pull_request.number }}
      # Add the model_url input to specify a different model
      model_url: 'https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf'
    secrets: inherit
```

### Workflow Inputs

Here are the available inputs for the reusable workflow:

| Input         | Description                                                                 | Required | Default                                                                                                      |
|---------------|-----------------------------------------------------------------------------|----------|--------------------------------------------------------------------------------------------------------------|
| `pr_number`   | The number of the pull request to review.                                   | `true`   | `N/A`                                                                                                        |
| `model_url`   | The URL of the GGUF model to use for the review.                            | `false`  | `https://huggingface.co/QuantFactory/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf` |
