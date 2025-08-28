import os
import yaml
from openai import OpenAI

# --- Absolute Path Setup ---
# Get the absolute path of the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# Get the project root directory by going one level up from the script directory
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))

# --- Configuration ---
NOTES_DIR = os.path.join(PROJECT_ROOT, "10 Notes")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output", "structured")
SYSTEM_PROMPT_FILE = os.path.join(SCRIPT_DIR, "system_prompt.md")
OPENAI_BASE_URL = "http://localhost:1234/v1"
OPENAI_API_KEY = "not-needed"  # LM Studio ignores this
MODEL = "openai/gpt-oss-20b"
TEMPERATURE = 0.7

# --- Setup ---
client = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)

def get_system_prompt(file_path):
    """Reads the system prompt from a file, with a fallback."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
Du bist ein hilfreicher Assistent, der Notizen in ein strukturiertes Markdown-Format mit YAML-Metadaten umwandelt.
Die gesamte Ausgabe muss auf Deutsch sein.
Analysiere den Inhalt der Notiz und die Liste aller verfügbaren Notizen, um relevante Metadaten zu erstellen.

Das YAML-Frontmatter sollte die folgenden Felder enthalten:
- title: Ein prägnanter, aussagekräftiger Titel für die Notiz.
- tags: Eine Liste von 1-5 relevanten Schlüsselwörtern (Tags).
- aliases: Eine Liste von alternativen Namen oder Synonymen für den Titel.
- related: Eine Liste von 1-3 verwandten Notiz-Dateinamen aus der bereitgestellten Liste. Wähle nur die relevantesten aus.

Der Hauptteil der Notiz sollte eine prägnante Zusammenfassung des Inhalts in deutscher Sprache sein.
"""

def get_all_notes(directory):
    """Gets a list of all files in the specified directory."""
    try:
        return [
            f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))
        ]
    except FileNotFoundError:
        print(f"Fehler: Das Verzeichnis '{directory}' wurde nicht gefunden.")
        return None

def create_user_prompt(filename, content, all_files):
    """Creates the user prompt for the OpenAI API call."""
    file_list_context = "Hier sind alle verfügbaren Notizen:\n" + "\n".join(all_files)
    return f"""{file_list_context}

Hier ist der Inhalt der Notiz '{filename}':

{content}

Bitte formatiere diese Notiz neu. Erstelle ein YAML-Frontmatter mit den Feldern 'title', 'tags', 'aliases' und 'related'.
Schreibe dann eine Zusammenfassung des Inhalts auf Deutsch.
"""

def process_note(filename, notes_dir, all_files, system_prompt):
    """Processes a single note file."""
    file_path = os.path.join(notes_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        print(f"--- Verarbeite {filename} ---")

        user_prompt = create_user_prompt(filename, content, all_files)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
        )

        response_content = response.choices[0].message.content
        return response_content

    except Exception as e:
        print(f"Konnte die Datei {filename} nicht verarbeiten. Fehler: {e}")
        return None

def save_reformatted_note(filename, content, output_dir):
    """Saves the reformatted note to the output directory."""
    if not content:
        print("Kein Inhalt in der Antwort.")
        return

    try:
        # The model might return the YAML block inside a markdown code block
        if content.startswith("```yaml"):
            content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
        elif content.startswith("```"):
             content = content[3:]
             if content.endswith("```"):
                content = content[:-3]


        # Ensure there is a newline after the YAML frontmatter
        parts = content.split("---")
        if len(parts) > 2:
            yaml_part = parts[1]
            body_part = "---".join(parts[2:])
            # Check if there is content in the body part before adding newlines
            if body_part.strip():
                 content = f"---{yaml_part}---\n\n{body_part.strip()}"
            else:
                 content = f"---{yaml_part}---"


        output_filename = os.path.splitext(filename)[0] + ".md"
        output_path = os.path.join(output_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as out_f:
            out_f.write(content)
        print(f"Strukturierte Ausgabe in {output_path} gespeichert")

    except Exception as e:
        print(f"Fehler beim Speichern der formatierten Notiz: {e}")
        print("Rohe Antwort:")
        print(content)


def main():
    """Main function to process all notes."""
    system_prompt = get_system_prompt(SYSTEM_PROMPT_FILE)
    all_files = get_all_notes(NOTES_DIR)

    if all_files is None:
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for filename in all_files:
        reformatted_content = process_note(filename, NOTES_DIR, all_files, system_prompt)
        if reformatted_content:
            save_reformatted_note(filename, reformatted_content, OUTPUT_DIR)
        print("-" * 50)

if __name__ == "__main__":
    main()
