---
name: bedrock-vision
description: >
  Analyze images from the workspace by extracting technical metadata and generating
  AI-powered descriptions via Amazon Bedrock. Use when the user references an image file
  or asks you to look at, describe, or analyze an image. Activate whenever you see image
  file paths (.png, .jpg, .jpeg, .gif, .webp, .bmp, .tiff) mentioned in conversation.
compatibility: Kiro IDE, Claude Code, Codex, Cursor
metadata:
  author: ks-ai-coding-kit
  version: "1.0"
---

# Bedrock Vision

This skill lets you analyze image files from the user's workspace. It extracts technical metadata (dimensions, file size, MIME type, bit depth, channels) and generates an AI-powered description using a Bedrock vision model.

## Dependencies

- Python 3.10+
- `boto3` — AWS SDK
- `Pillow` — image metadata extraction

Install if needed:

```bash
pip install boto3 Pillow
```

## How to Use

### Step 1: Ask the User Which Model to Use

**Before running the script**, always present the user with these model choices:

1. Amazon Nova 2 Lite | `us.amazon.nova-2-lite-v1:0`
2. Anthropic Claude Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6`
3. Qwen3 VL 235B A22B | `qwen.qwen3-vl-235b-a22b`
4. Other

If the user chooses **Other**, ask them for the exact Bedrock model ID to use.

**Do not skip this step.** Always ask, every time. Do not assume a default.

### Step 2: Run the Script

Once you have the model choice, run the script:

```bash
python skills/bedrock-vision/scripts/describe.py <image_path> --model <chosen_model_id>
```

### Customizing the Prompt

By default, the script uses a general-purpose description prompt. **You should override this** with a prompt tailored to what the user is actually asking about:

```bash
python skills/bedrock-vision/scripts/describe.py photo.png --model us.amazon.nova-2-lite-v1:0 --prompt "What text is visible in this image? Transcribe it exactly."
```

```bash
python skills/bedrock-vision/scripts/describe.py diagram.png --model us.anthropic.claude-sonnet-4-6 --prompt "Describe the architecture shown in this diagram, including all components and their connections."
```

### Other Options

```bash
# Use a specific AWS profile
python skills/bedrock-vision/scripts/describe.py photo.png --model us.amazon.nova-2-lite-v1:0 --profile admin-933

# Use a different region
python skills/bedrock-vision/scripts/describe.py photo.png --model us.amazon.nova-2-lite-v1:0 --region us-west-2

# Get output as JSON (useful for programmatic consumption)
python skills/bedrock-vision/scripts/describe.py photo.png --model us.amazon.nova-2-lite-v1:0 --json
```

### Example Output

```
## Image Metadata

- **File**: screenshot.png
- **Path**: /Users/kris/project/screenshot.png
- **Dimensions**: 1920 × 1080 px
- **File size**: 245.3 KB (251,187 bytes)
- **MIME type**: image/png
- **Bit depth**: 32-bit
- **Channels**: 4 (8-bit per channel, RGBA)

## AI Description

The image shows a desktop application window with a dark theme...
```

## When to Use

1. **When the user mentions an image file.** If they say "look at screenshot.png" or "what's in assets/logo.png", activate this skill and run the script.
2. **When the user asks about visual content.** Questions like "what does this diagram show?" or "read the text in this image" — use the `--prompt` flag to tailor the vision model's focus.
3. **When you need image metadata.** If the user asks about dimensions, file size, or format of an image, this script provides that without needing the vision model (though it runs both by default).

## Important

- **Always ask which model to use.** Present the four options listed above every time. Never skip this or assume a default.
- **Tailor the prompt.** Don't just use the default prompt. Craft a `--prompt` that matches what the user is actually asking. This dramatically improves the quality of the response.
- **Use the output naturally.** Don't dump the raw output to the user. Read it, understand it, and incorporate it into your response as if you looked at the image yourself.
- **Handle errors gracefully.** If the script fails (missing credentials, unsupported format), tell the user what went wrong and suggest alternatives (like dragging the image into chat).
