import sys
from gi.repository import Gtk, Adw, Gdk, Gio
from whisp.window import WhispWindow

class WhispApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.Whisp", flags=Gio.ApplicationFlags.HANDLES_OPEN)

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.set_accels_for_action("win.new-note", ["<Ctrl>n"])
        self.set_accels_for_action("win.delete-note", ["<Ctrl>d", "<Ctrl>Delete"])
        self.set_accels_for_action("win.preferences", ["<Ctrl>comma"])
        self.set_accels_for_action("win.toggle-wysiwyg", ["<Ctrl>e"])
        self.set_accels_for_action("win.undo-delete", ["<Ctrl><Shift>t"])
        self.set_accels_for_action("win.show-shortcuts", ["<Ctrl>question"])
        self.set_accels_for_action("win.nav-next", ["<Ctrl>bracketright"])
        self.set_accels_for_action("win.nav-prev", ["<Ctrl>bracketleft"])

        # Cohesive Background CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            window.background { background-color: @view_bg_color; }
            textview { background-color: transparent; }
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
    app = WhispApp()
    return app.run(sys.argv)
