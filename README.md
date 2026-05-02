# Nota

<img width="450" height="450" alt="image" src="https://github.com/user-attachments/assets/baed3f6d-71b5-4d69-9309-f8dd7e7b05da" />


Nota is a minimalist, lightning-fast, and gesture-driven note-taking application built for the GNOME desktop environment. Designed to act as a seamless desktop scratchpad, it offers distraction-free Markdown editing while blending perfectly with modern GNOME aesthetics using GTK4 and Libadwaita.


## Features

- **Live Markdown Highlighting**: Real-time syntax highlighting for headings, bold, italics, underlines (`<u>`), inline code blocks, bullet points, and numbered lists.
- **Gesture Navigation**: Fluidly swipe between your recent notes using 2-finger touchpad gestures.
- **Keyboard-Centric Workflow**: 
  - `Ctrl+N` to instantly create a new note from anywhere in the app.
  - `Ctrl+B`, `Ctrl+I`, `Ctrl+U` to quickly format text in the editor.
- **Lightning Fast Performance**: Automatically keeps only your top 10 most recently modified notes in the active carousel for instant startup, no matter how many notes you have.
- **Robust Note Management**: A unified searchable dropdown lets you access all your notes.
- **Tagging System**: Add hashtags (e.g., `#urgent`, `#todo`) anywhere in your note, and instantly filter by them in the search menu.
- **Custom Storage Location**: Save your notes wherever you want via the Preferences menu—perfect for syncing with Nextcloud or Dropbox. All notes are saved as plain `.md` files.
- **Safe Deletion**: Deleted notes aren't permanently erased; they are moved to a hidden `.trash/` folder inside your notes directory.

## Installation

Nota uses the standard Meson build system, making it easy to compile and install on any Linux distribution.

### Prerequisites

Ensure you have the following dependencies installed:
- `python3`
- `meson`
- `ninja`
- `python3-gi` (PyGObject)
- `libadwaita` & `gtk4`

### Building from Source

1. Clone the repository and navigate into the project directory:
   ```bash
   git clone <your-repo-url>
   cd Nota
   ```

2. Setup the build directory:
   ```bash
   meson setup builddir
   ```

3. Compile and install the application globally:
   ```bash
   sudo meson install -C builddir
   ```

Once installed, you can launch Nota directly from your application launcher (app grid), or run `nota` from the terminal.

## Architecture

Nota strictly follows the GNOME HIG (Human Interface Guidelines). It leverages `Adw.Carousel` for its swipeable interface and uses an elegant `Gtk.TextView` wrapper to instantly parse and decorate Markdown text using `Gtk.TextTag`.

## License

*(Add your license information here, e.g., MIT, GPLv3)*
