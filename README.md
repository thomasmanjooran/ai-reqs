# AI-Reqs: The Intelligent requirements.txt Generator

**Tired of messy `requirements.txt` files? Frustrated that tools like `pipreqs` fail on your complex data science projects and Jupyter Notebooks?**

`ai-reqs` is a next-generation dependency scanner for Python that uses the power of Google's Gemini AI to solve the problems other tools can't. It intelligently scans your project, including `.py` files and `.ipynb` notebooks, and generates a clean, accurate `requirements.txt` file.

## Why is `ai-reqs` better?

| Feature | `pipreqs` / `pipreqsnb` | `ai-reqs` (This Tool) |
| :--- | :--- | :--- |
| **Notebook Support** | Often fails or requires a separate fork (`pipreqsnb`). | ✅ **Yes, built-in.** |
| **Dependency Resolution** | Uses a static, internal list of common packages. | 🧠 **AI-Powered.** Uses Gemini to resolve even the most obscure or confusing imports (`cv2` -> `opencv-python`, `PIL` -> `Pillow`). |
| **Robustness** | Can crash on files with non-standard characters. | ✅ **Handles encoding errors** gracefully. |
| **Future-Proof** | Needs to be updated manually for new packages. | 🚀 **Always up-to-date.** The AI can identify new packages as they are released. |

## Installation

```bash
pip install ai-reqs
```

## Quick Start

1.  **Get a Gemini API Key:**
    * Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create an API key.

2.  **Set the API Key:**
    You can either set it as an environment variable (recommended) or pass it as an argument.

    ```bash
    # Recommended: Set as an environment variable
    export GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

3.  **Run `ai-reqs`:**
    Navigate to your project's root directory in your terminal and run the command:

    ```bash
    ai-reqs
    ```

    That's it! A clean `requirements.txt` will be generated in your project directory.

## Usage

The command-line interface is simple and straightforward.

## Usage

```text
usage: ai-reqs [-h] [--path PATH] [--api-key API_KEY]

Generate a requirements.txt file for a Python project using AI for dependency resolution.

options:
  -h, --help         show this help message and exit
  --path PATH        The path to the project directory to scan. Defaults to
                     the current directory.
  --api-key API_KEY  Your Gemini API key. Can also be set via the
                     GEMINI_API_KEY environment variable.
```

## How It Works

The tool scans all Python scripts and Jupyter Notebooks in your project to find all `import` statements. It then uses a hybrid approach to find the correct package for each import:

1.  It first checks your local Python environment's metadata.
2.  For any import it can't resolve locally (like `sklearn` or `cv2`), it queries the Gemini API to get the correct `pip` package name.
3.  Finally, it generates a `requirements.txt` file with the correct package names and their currently installed versions.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License.