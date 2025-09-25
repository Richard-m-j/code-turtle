#!/bin/bash
set -e

# Step 1: Generate Model URL Hash
MODEL_HASH=$(echo -n "$MODEL_URL" | sha256sum | cut -d' ' -f1)

# Step 2: Cache and Download AI Model
if [ ! -f ./model.gguf ]; then
  echo "Downloading AI Model..."
  curl -L -o ./model.gguf "$MODEL_URL"
fi

# Step 3: Construct Prompt
PROMPT_FILE="prompt.txt"
SYSTEM_PROMPT="You are an expert code reviewer AI..." # Truncated for brevity
CODE_DIFF=$(cat code.diff)
echo "$SYSTEM_PROMPT" > $PROMPT_FILE
echo "" >> $PROMPT_FILE
echo "Here is the code diff to review:" >> $PROMPT_FILE
echo '```diff' >> $PROMPT_FILE
echo "$CODE_DIFF" >> $PROMPT_FILE
echo '```' >> $PROMPT_FILE
echo "" >> $PROMPT_FILE
echo "Please provide your review now." >> $PROMPT_FILE

# Step 4: Run LLM Inference
/app/llama-cli \
  -m ./model.gguf \
  -f prompt.txt \
  --ctx-size 4096 \
  --n-predict 1024 \
  --temp 0.2 \
  > review_output.txt

# Step 5: Format and Post Comment
echo "### 🤖 AI Code Review" > final_comment.md
echo "" >> final_comment.md
echo "Here are some suggestions based on the latest changes..." >> final_comment.md
echo "" >> final_comment.md
echo "---" >> final_comment.md
echo "" >> final_comment.md
cat review_output.txt >> final_comment.md

gh pr comment $PR_NUMBER --repo $GH_REPO --body-file final_comment.md