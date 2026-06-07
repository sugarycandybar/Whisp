import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio
from whisp.window import WhispWindow

IS_DEV_MODE = "--dev" in sys.argv

class WhispApp(Adw.Application):
    def __init__(self):
        app_id = "io.github.tanaybhomia.Whisp.Devel" if IS_DEV_MODE else "io.github.tanaybhomia.Whisp"
        super().__init__(application_id=app_id, flags=Gio.ApplicationFlags.HANDLES_OPEN)

    def do_startup(self):
        Adw.Application.do_startup(self)
        
        # Add local icon directory to search path for testing
        import os
        from pathlib import Path
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_dir = Path(__file__).parent.parent.parent / "data" / "icons"
        if icon_dir.exists():
            icon_theme.add_search_path(str(icon_dir))
            
        self.set_accels_for_action("win.new-note", ["<Ctrl>n"])
        self.set_accels_for_action("win.delete-note", ["<Ctrl>d", "<Ctrl>Delete"])
        self.set_accels_for_action("win.preferences", ["<Ctrl>comma"])
        self.set_accels_for_action("win.toggle-wysiwyg", ["<Ctrl>e"])
        self.set_accels_for_action("win.undo-delete", ["<Ctrl><Shift>t"])
        self.set_accels_for_action("win.show-shortcuts", ["<Ctrl>question"])
        self.set_accels_for_action("win.nav-next", ["<Ctrl>bracketright"])
        self.set_accels_for_action("win.nav-prev", ["<Ctrl>bracketleft"])
        self.set_accels_for_action("win.search", ["<Ctrl>f"])
        self.set_accels_for_action("win.quit", ["<Ctrl>q"])

        # Cohesive Background CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window.background { background-color: @view_bg_color; }
            textview { 
                background-color: transparent; 
            }
            textview > text {
                padding: 0 8px; /* Prevent left-edge glyph clipping */
            }
            toast {
                margin-left: 48px;
                margin-right: 48px;
            }
            window.about image.icon { transform: scale(0.8); }

            /* Paper Themes */
            .paper-dotted {
                background-image: radial-gradient(circle, alpha(currentColor, 0.15) 1px, transparent 1px);
                background-size: 20px 20px;
                background-position: 0 0;
            }
            .paper-grid {
                background-image: linear-gradient(to right, alpha(currentColor, 0.1) 1px, transparent 1px),
                                  linear-gradient(to bottom, alpha(currentColor, 0.1) 1px, transparent 1px);
                background-size: 14px 14px;
                background-position: 0 0;
            }
            .paper-large_grid {
                background-image: linear-gradient(to right, alpha(currentColor, 0.1) 1px, transparent 1px),
                                  linear-gradient(to bottom, alpha(currentColor, 0.1) 1px, transparent 1px);
                background-size: 36px 36px;
                background-position: 0 0;
            }
            .paper-blank { background-image: none; }
            
            /* Snippet styling */
            .theme-snippet-btn {
                padding: 4px;
                border-radius: 12px;
                border: 2px solid transparent;
            }
            .theme-snippet-btn:checked {
                border-color: @accent_bg_color;
                background-color: transparent;
            }
            .theme-snippet-preview {
                min-width: 120px;
                min-height: 80px;
                border-radius: 8px;
                border: 1px solid alpha(currentColor, 0.15);
                background-color: @view_bg_color;
                padding: 12px 8px;
            }
            .fake-text-line {
                background-color: alpha(currentColor, 0.3);
                border-radius: 2px;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = WhispWindow(application=self)
            win.load_notes()
        win.present()

    def do_open(self, files, n_files, hint):
        win = self.props.active_window
        if not win:
            win = WhispWindow(application=self)
            win.load_notes()
            
        for file in files:
            path = file.get_path()
            if path and path.endswith('.md'):
                # Check if it's already in the carousel
                found = False
                n_pages = win.carousel.get_n_pages()
                for i in range(n_pages):
                    editor = win.carousel.get_nth_page(i)
                    if str(editor.file_path) == path:
                        win.carousel.scroll_to(editor, True)
                        found = True
                        break
                
                # If not, add it
                if not found:
                    win.add_note(path)
                    
        win.present()

def main():
    if '--dev' in sys.argv:
        sys.argv.remove('--dev')
    app = WhispApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
