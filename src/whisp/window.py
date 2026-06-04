import re
import os
import shutil
from pathlib import Path
from gi.repository import Gtk, Adw, Gdk, Gio, GLib, Pango
from whisp.config import config, DATA_DIR, TRASH_DIR
from whisp.editor import NoteEditor

class ThemeSnippet(Gtk.ToggleButton):
    def __init__(self, theme_id, group=None):
        super().__init__(group=group)
        self.theme_id = theme_id
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.add_css_class("theme-snippet-btn")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("theme-snippet-preview")
        box.add_css_class(f"paper-{theme_id}")
        
        # Add fake text lines to simulate an editor
        for width in [60, 80, 40]:
            line = Gtk.Box()
            line.add_css_class("fake-text-line")
            line.set_size_request(width, 4)
            line.set_halign(Gtk.Align.START)
            box.append(line)
            
        self.set_child(box)

shortcuts_xml = """
<interface>
  <object class="GtkShortcutsWindow" id="shortcuts_window">
    <property name="modal">True</property>
    <child>
      <object class="GtkShortcutsSection">
        <property name="section-name">editor</property>
        <property name="max-height">12</property>
        
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title">General</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Create New Note</property>
                <property name="accelerator">&lt;Primary&gt;n</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Delete Note</property>
                <property name="accelerator">&lt;Primary&gt;Delete</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Undo Delete</property>
                <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;t</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Previous Note</property>
                <property name="accelerator">&lt;Primary&gt;bracketleft</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Next Note</property>
                <property name="accelerator">&lt;Primary&gt;bracketright</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Preferences</property>
                <property name="accelerator">&lt;Primary&gt;comma</property>
              </object>
            </child>
          </object>
        </child>
        
        <child>
          <object class="GtkShortcutsGroup">
            <property name="title">Editor</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Search Notes</property>
                <property name="accelerator">&lt;Primary&gt;f</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Toggle Checkbox</property>
                <property name="accelerator">&lt;Primary&gt;s</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Paste Plain Text</property>
                <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;v</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Shorten Selected URL</property>
                <property name="accelerator">&lt;Primary&gt;&lt;Shift&gt;l</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Bold Text</property>

                <property name="accelerator">&lt;Primary&gt;b</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Italic Text</property>
                <property name="accelerator">&lt;Primary&gt;i</property>
              </object>
            </child>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Underline Text</property>
                <property name="accelerator">&lt;Primary&gt;u</property>
              </object>
            </child>
          </object>
        </child>

        <child>
          <object class="GtkShortcutsGroup">
            <property name="title">Modes</property>
            <child>
              <object class="GtkShortcutsShortcut">
                <property name="title">Toggle WYSIWYG Mode</property>
                <property name="accelerator">&lt;Primary&gt;e</property>
              </object>
            </child>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>
"""

class WhispWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Window State
        width = config.get("window_width")
        height = config.get("window_height")
        if width is None or height is None:
            width = 450
            height = 700
        self.set_default_size(int(width), int(height))
        if config.get("is_maximized"):
            self.maximize()
            
        from whisp.main import IS_DEV_MODE
        title = "Whisp (Development)" if IS_DEV_MODE else "Whisp"
        self.set_title(title)
        self.connect("close-request", self.on_close_request)
        
        # Font and Theme styling
        self.css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.apply_theme()
        
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.box)
        self.set_content(self.toast_overlay)
        
        self.last_deleted_file = None

        # Actions
        new_note_action = Gio.SimpleAction.new("new-note", None)
        new_note_action.connect("activate", self.on_new_note)
        self.add_action(new_note_action)
        
        undo_action = Gio.SimpleAction.new("undo-delete", None)
        undo_action.connect("activate", self.on_undo_delete)
        self.add_action(undo_action)
        
        shortcuts_action = Gio.SimpleAction.new("show-shortcuts", None)
        shortcuts_action.connect("activate", self.on_show_shortcuts)
        self.add_action(shortcuts_action)
        
        del_note_action = Gio.SimpleAction.new("delete-note", None)
        del_note_action.connect("activate", self.on_delete_note)
        self.add_action(del_note_action)
        
        pref_action = Gio.SimpleAction.new("preferences", None)
        pref_action.connect("activate", self.on_preferences)
        self.add_action(pref_action)
        
        nav_next_action = Gio.SimpleAction.new("nav-next", None)
        nav_next_action.connect("activate", self.on_nav_next)
        self.add_action(nav_next_action)
        
        nav_prev_action = Gio.SimpleAction.new("nav-prev", None)
        nav_prev_action.connect("activate", self.on_nav_prev)
        self.add_action(nav_prev_action)
        
        wysiwyg_action = Gio.SimpleAction.new("toggle-wysiwyg", None)
        wysiwyg_action.connect("activate", self.on_wysiwyg_shortcut)
        self.add_action(wysiwyg_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)

        # HeaderBar
        self.header_bar = Adw.HeaderBar()
        self.header_bar.add_css_class("flat")
        self.box.append(self.header_bar)
        
        # WYSIWYG Toggle Button
        self.wysiwyg_btn = Gtk.ToggleButton(icon_name="view-reveal-symbolic")
        self.wysiwyg_btn.set_tooltip_text("Toggle Live Formatting")
        self.wysiwyg_btn.set_active(config.get("wysiwyg_mode", False))
        self.wysiwyg_btn.connect("toggled", self.on_wysiwyg_toggled)
        self.header_bar.pack_start(self.wysiwyg_btn)

        # Delete Note Button
        del_btn = Gtk.Button(icon_name="user-trash-symbolic")
        del_btn.set_action_name("win.delete-note")
        del_btn.add_css_class("destructive-action")
        self.header_bar.pack_start(del_btn)

        # Search Toggle Button
        self.search_btn = Gtk.MenuButton()
        self.search_btn.set_icon_name("system-search-symbolic")
        self.header_bar.pack_end(self.search_btn)

        self.popover = Gtk.Popover()
        self.search_btn.set_popover(self.popover)
        self.popover.connect("notify::visible", self.on_popover_visible)

        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        popover_box.set_margin_top(12)
        popover_box.set_margin_bottom(12)
        popover_box.set_margin_start(12)
        popover_box.set_margin_end(12)
        self.popover.set_child(popover_box)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("search-changed", self.on_search_changed)
        popover_box.append(self.search_entry)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(200)
        scrolled.set_min_content_width(200)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        popover_box.append(scrolled)

        self.note_listbox = Gtk.ListBox()
        self.note_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.note_listbox.add_css_class("boxed-list")
        self.note_listbox.connect("row-activated", self.on_note_row_activated)
        scrolled.set_child(self.note_listbox)


        # Hamburger menu
        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("open-menu-symbolic")
        
        theme_item = Gio.MenuItem.new(None, None)
        theme_item.set_attribute_value("custom", GLib.Variant.new_string("theme-switcher"))
        
        main_menu = Gio.Menu()
        main_menu.append_item(theme_item)
        
        section = Gio.Menu()
        section.append("Keyboard Shortcuts", "win.show-shortcuts")
        section.append("Preferences", "win.preferences")
        section.append("About Whisp", "win.about")
        main_menu.append_section(None, section)
        
        popover = Gtk.PopoverMenu.new_from_model(main_menu)
        
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        theme_box.set_halign(Gtk.Align.CENTER)
        theme_box.set_margin_top(8)
        theme_box.set_margin_bottom(8)
        theme_box.set_margin_start(12)
        theme_box.set_margin_end(12)
        
        self.btn_system = Gtk.ToggleButton()
        self.btn_system.add_css_class("theme-btn")
        self.btn_system.add_css_class("system")
        self.btn_system.connect("toggled", self.on_theme_btn_toggled, "system")
        
        self.btn_light = Gtk.ToggleButton()
        self.btn_light.add_css_class("theme-btn")
        self.btn_light.add_css_class("light")
        self.btn_light.set_group(self.btn_system)
        self.btn_light.connect("toggled", self.on_theme_btn_toggled, "light")
        
        self.btn_dark = Gtk.ToggleButton()
        self.btn_dark.add_css_class("theme-btn")
        self.btn_dark.add_css_class("dark")
        self.btn_dark.set_group(self.btn_system)
        self.btn_dark.connect("toggled", self.on_theme_btn_toggled, "dark")
        
        theme_box.append(self.btn_system)
        theme_box.append(self.btn_light)
        theme_box.append(self.btn_dark)
        
        popover.add_child(theme_box, "theme-switcher")
        self.menu_button.set_popover(popover)
        self.header_bar.pack_end(self.menu_button)

        # Apply initial theme state
        current_theme = config.get("color_scheme", "system")
        if current_theme == "light":
            self.btn_light.set_active(True)
        elif current_theme == "dark":
            self.btn_dark.set_active(True)
        else:
            self.btn_system.set_active(True)
            
        self._apply_color_scheme(current_theme)

        # Carousel
        self.carousel = Adw.Carousel()
        self.carousel.set_spacing(16)
        self.carousel.set_interactive(True)
        self.carousel.connect("page-changed", self.on_page_changed)
        self.box.append(self.carousel)

    def on_theme_btn_toggled(self, btn, scheme):
        if btn.get_active():
            config.set("color_scheme", scheme)
            self._apply_color_scheme(scheme)

    def _apply_color_scheme(self, scheme):
        manager = Adw.StyleManager.get_default()
        if scheme == "light":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif scheme == "dark":
            manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def _get_dynamic_version(self):
        import xml.etree.ElementTree as ET
        from pathlib import Path
        try:
            # Try Flatpak path first
            meta_path = Path("/app/share/metainfo/io.github.tanaybhomia.Whisp.metainfo.xml")
            if not meta_path.exists():
                # Fallback to local source tree
                meta_path = Path(__file__).parent.parent.parent / "data" / "io.github.tanaybhomia.Whisp.metainfo.xml"
                
            tree = ET.parse(meta_path)
            root = tree.getroot()
            releases = root.find("releases")
            if releases is not None:
                latest_release = releases.find("release")
                if latest_release is not None:
                    return latest_release.attrib.get("version", "Unknown")
        except Exception:
            pass
        return "Unknown"

    def on_about(self, action, param):
        version = self._get_dynamic_version()
        about = Adw.AboutWindow(
            application_name="Whisp",
            application_icon="io.github.tanaybhomia.Whisp",
            developer_name="Tanay Bhomia",
            developers=["Tanay Bhomia"],
            version=version,
            website="https://github.com/tanaybhomia/Whisp",
            issue_url="https://github.com/tanaybhomia/Whisp/issues",
            license_type=Gtk.License.GPL_3_0
        )
        about.set_default_size(360, -1)
        about.set_transient_for(self)
        about.present()

    def on_nav_next(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            return
        current = int(round(self.carousel.get_position()))
        if current < n_pages - 1:
            editor = self.carousel.get_nth_page(current + 1)
            self.carousel.scroll_to(editor, True)
            GLib.idle_add(lambda: [editor.textview.grab_focus(), False][-1])
            
    def on_nav_prev(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            return
        current = int(round(self.carousel.get_position()))
        if current > 0:
            editor = self.carousel.get_nth_page(current - 1)
            self.carousel.scroll_to(editor, True)
            GLib.idle_add(lambda: [editor.textview.grab_focus(), False][-1])

    def on_wysiwyg_toggled(self, btn):
        config.set("wysiwyg_mode", btn.get_active())
        for i in range(self.carousel.get_n_pages()):
            editor = self.carousel.get_nth_page(i)
            editor.highlighter.highlight()
            
    def on_wysiwyg_shortcut(self, action, param):
        self.wysiwyg_btn.set_active(not self.wysiwyg_btn.get_active())

    def on_show_shortcuts(self, action, param):
        builder = Gtk.Builder.new_from_string(shortcuts_xml, -1)
        win = builder.get_object("shortcuts_window")
        win.set_transient_for(self)
        win.present()

    def load_notes(self):
        files = sorted(DATA_DIR.glob("*.md"), key=lambda f: os.path.getmtime(f) if f.exists() else 0, reverse=True)
        # Load up to 10 most recently modified notes
        recent_files = files[:10]
        
        if not recent_files:
            self.add_note(grab_focus=False)
        else:
            # Reverse back to append in chronological order so newest is at the end
            for f in reversed(recent_files):
                self.add_note(f, grab_focus=False)
        
        self.ensure_empty_note_at_end()
        
        n_pages = self.carousel.get_n_pages()
        if n_pages > 0:
            target_idx = n_pages - 2 if n_pages > 1 else 0
            
            startup_behavior = config.get("startup_behavior", "last_note")
            if startup_behavior == "empty_note":
                target_idx = n_pages - 1
            else:
                last_active = config.get("last_active_note")
                if last_active:
                    for i in range(n_pages):
                        if str(self.carousel.get_nth_page(i).file_path) == last_active:
                            target_idx = i
                            break
                        
            target_editor = self.carousel.get_nth_page(target_idx)
            
            def restore_session():
                self.carousel.scroll_to(target_editor, False)
                target_editor.textview.grab_focus()
                buffer = target_editor.buffer
                buffer.place_cursor(buffer.get_end_iter())
                self.update_title()
                return False
            
            GLib.idle_add(restore_session)
            GLib.timeout_add(50, restore_session)
            GLib.timeout_add(200, restore_session)
            GLib.timeout_add(500, restore_session)

    def add_note(self, file_path=None, grab_focus=True, index=None):
        editor = NoteEditor(file_path=file_path, on_title_changed=self.on_editor_title_changed)
        if index is not None:
            self.carousel.insert(editor, index)
        else:
            self.carousel.append(editor)
        if grab_focus:
            def grab_it():
                self.carousel.scroll_to(editor, False)
                editor.textview.grab_focus()
                self.update_title()
                return False
            GLib.idle_add(grab_it)
            GLib.timeout_add(50, grab_it)
            GLib.timeout_add(150, grab_it)
        self.update_line_spacing()

    def ensure_empty_note_at_end(self):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            self.add_note(grab_focus=False)
            return
            
        # If there are any empty notes that are NOT at the end, remove them
        # (This fixes the "empty note at the start" bug)
        for i in range(n_pages - 1, -1, -1):
            editor = self.carousel.get_nth_page(i)
            if editor.is_empty():
                if i != self.carousel.get_n_pages() - 1:
                    self.carousel.remove(editor)
                    
        # Check if the new last note is empty
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            self.add_note(grab_focus=False)
            return
            
        last_editor = self.carousel.get_nth_page(n_pages - 1)
        if not last_editor.is_empty():
            self.add_note(grab_focus=False)

    def on_new_note(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages > 0:
            self.carousel.scroll_to(self.carousel.get_nth_page(n_pages - 1), True)

    def on_undo_delete(self, action=None, param=None):
        if not self.last_deleted_file:
            return
            
        trash_path = TRASH_DIR / self.last_deleted_file
        data_path = DATA_DIR / self.last_deleted_file
        
        if trash_path.exists():
            shutil.move(str(trash_path), str(data_path))
            idx = getattr(self, 'last_deleted_index', None)
            self.add_note(data_path, grab_focus=True, index=idx)
            self.last_deleted_file = None
            self.last_deleted_index = None

    def on_delete_note(self, action=None, param=None):
        n_pages = self.carousel.get_n_pages()
        if n_pages == 0:
            return

        current_page_idx = int(round(self.carousel.get_position()))
        editor = self.carousel.get_nth_page(current_page_idx)

        # Don't allow deleting an already empty note (prevents app locking bug)
        if editor.is_empty():
            return

        # Skip confirmation if user disabled it
        if not config.get("confirm_delete", True):
            self.perform_delete(editor)
            return

        title = editor.get_title()
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Note?",
            body=f"“{title}” will be moved to the trash. You can undo this with Ctrl+Shift+T.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self.on_delete_dialog_response, editor)
        dialog.present()

    def on_delete_dialog_response(self, dialog, response, editor):
        if response == "delete":
            self.perform_delete(editor)

    def perform_delete(self, editor):
        # Cancel any pending save timeout to prevent a "ghost note" from writing itself to disk after deletion
        if hasattr(editor, 'save_timeout_id') and editor.save_timeout_id:
            GLib.source_remove(editor.save_timeout_id)
            editor.save_timeout_id = 0

        # Find index to allow restoring to the exact same position
        idx = -1
        for i in range(self.carousel.get_n_pages()):
            if self.carousel.get_nth_page(i) == editor:
                idx = i
                break
        self.last_deleted_index = idx if idx != -1 else None

        toast_msg = "Note deleted"
        if editor.file_path.exists():
            try:
                TRASH_DIR.mkdir(parents=True, exist_ok=True)
                dest_path = TRASH_DIR / editor.file_path.name
                
                # shutil.move crashes if the destination file already exists
                if dest_path.exists():
                    dest_path.unlink()
                    
                # Try to move to trash first
                shutil.move(str(editor.file_path), str(dest_path))
                self.last_deleted_file = editor.file_path.name
            except Exception as e:
                # Fallback
                try:
                    editor.file_path.unlink(missing_ok=True)
                    self.last_deleted_file = None
                    toast_msg = f"Permanent delete fallback (Error: {str(e)})"
                except Exception as e2:
                    toast_msg = f"Failed to delete completely: {e2}"
        else:
            # Note was never saved to disk
            self.last_deleted_file = None

        if hasattr(self, 'current_toast') and self.current_toast:
            self.current_toast.dismiss()

        self.current_toast = Adw.Toast.new(toast_msg)
        if self.last_deleted_file:
            self.current_toast.set_button_label("Undo")
            self.current_toast.set_action_name("win.undo-delete")
        self.current_toast.set_timeout(5)
        self.toast_overlay.add_toast(self.current_toast)

        self.carousel.remove(editor)

        if self.carousel.get_n_pages() == 0:
            self.add_note()
        else:
            self.update_title()

    def on_page_changed(self, carousel, index):
        self.update_title()
        editor = carousel.get_nth_page(int(round(index)))
        if editor:
            GLib.idle_add(lambda: [editor.textview.grab_focus(), False][-1])

    def on_editor_title_changed(self, editor):
        self.ensure_empty_note_at_end()
        if self.carousel.get_n_pages() == 0:
            return
        current_page_idx = int(round(self.carousel.get_position()))
        if current_page_idx < self.carousel.get_n_pages():
            current_editor = self.carousel.get_nth_page(current_page_idx)
            if editor == current_editor:
                self.update_title()

    def update_title(self):
        pass

    def on_popover_visible(self, popover, param):
        if popover.get_visible():
            self.search_entry.set_text("")
            self.populate_note_list()
            self.search_entry.grab_focus()

    def populate_note_list(self, search_text=""):
        # Clear existing rows
        while child := self.note_listbox.get_first_child():
            self.note_listbox.remove(child)
            
        search_text = search_text.lower()
        files = sorted(DATA_DIR.glob("*.md"), key=lambda f: os.path.getmtime(f) if f.exists() else 0, reverse=True)
        
        for f in files:
            content = f.read_text(encoding='utf-8') if f.exists() else ""
            first_line = content.split('\n')[0].strip() if content else ""
            title = re.sub(r'^#+\s*', '', first_line) if first_line else "New Note"
            
            tags = set(re.findall(r'#(\w+)', content))
            tag_str = " ".join([f"#{t}" for t in tags])
            
            if search_text:
                searchable = (title + " " + tag_str).lower()
                if search_text not in searchable:
                    continue
                    
            row = Gtk.ListBoxRow()
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            vbox.set_margin_start(12)
            vbox.set_margin_end(12)
            vbox.set_margin_top(8)
            vbox.set_margin_bottom(8)
            
            label = Gtk.Label(label=title, xalign=0)
            vbox.append(label)
            
            if tag_str:
                tag_label = Gtk.Label(label=tag_str, xalign=0)
                tag_label.add_css_class("dim-label")
                vbox.append(tag_label)
                
            row.set_child(vbox)
            row.file_path = f
            self.note_listbox.append(row)

    def on_search_changed(self, entry):
        self.populate_note_list(entry.get_text())

    def on_note_row_activated(self, listbox, row):
        file_path = getattr(row, 'file_path', None)
        if file_path:
            # Check if it's already in the carousel
            found = False
            for i in range(self.carousel.get_n_pages()):
                editor = self.carousel.get_nth_page(i)
                if editor.file_path == file_path:
                    self.carousel.scroll_to(editor, True)
                    found = True
                    break
            
            if not found:
                self.add_note(file_path)
            self.update_title()
        self.popover.popdown()

    def on_preferences(self, action, param):
        pref_window = Adw.PreferencesWindow(transient_for=self)
        page = Adw.PreferencesPage()
        
        # Appearance Group
        font_group = Adw.PreferencesGroup(title="Appearance")
        font_row = Adw.ActionRow(title="Editor Font")
        
        font_dialog = Gtk.FontDialog()
        font_btn = Gtk.FontDialogButton()
        font_btn.set_dialog(font_dialog)
        font_btn.set_valign(Gtk.Align.CENTER)
        
        font_name = config.get("font_name")
        if font_name:
            font_desc = Pango.FontDescription.from_string(font_name)
            font_btn.set_font_desc(font_desc)
            
        font_btn.connect("notify::font-desc", self.on_font_changed)
        font_row.add_suffix(font_btn)
        font_group.add(font_row)
        
        # Theme Snippets Group
        theme_group = Adw.PreferencesGroup(title="Paper Theme")
        
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        flowbox.set_max_children_per_line(3)
        flowbox.set_min_children_per_line(1)
        flowbox.set_row_spacing(12)
        flowbox.set_column_spacing(12)
        flowbox.set_margin_top(8)
        flowbox.set_margin_bottom(8)
        
        themes = ["blank", "dotted", "grid", "large_grid"]
        current_theme = config.get("paper_theme", "blank")
        
        group = None
        for t in themes:
            snippet = ThemeSnippet(t, group=group)
            if group is None:
                group = snippet
            if t == current_theme:
                snippet.set_active(True)
                
            snippet.connect("toggled", self.on_theme_snippet_toggled)
            flowbox.append(snippet)
            
        theme_group.add(flowbox)
        page.add(theme_group)
        
        # Line Spacing
        spacing_row = Adw.ActionRow(title="Line Spacing")
        spacing_model = Gtk.StringList.new(["1.0", "1.2", "1.5", "2.0"])
        spacing_dropdown = Gtk.DropDown(model=spacing_model)
        spacing_dropdown.set_valign(Gtk.Align.CENTER)
        
        current_spacing = config.get("line_spacing", "1.2")
        try:
            idx = ["1.0", "1.2", "1.5", "2.0"].index(current_spacing)
            spacing_dropdown.set_selected(idx)
        except ValueError:
            pass
            
        spacing_dropdown.connect("notify::selected-item", self.on_spacing_changed)
        spacing_row.add_suffix(spacing_dropdown)
        font_group.add(spacing_row)
        
        page.add(font_group)

        # Behavior Group
        behavior_group = Adw.PreferencesGroup(title="Behavior")
        
        startup_row = Adw.ActionRow(title="Startup Behavior")
        startup_model = Gtk.StringList.new(["Restore last active note", "Start with empty note"])
        startup_dropdown = Gtk.DropDown(model=startup_model)
        startup_dropdown.set_valign(Gtk.Align.CENTER)
        
        current_startup = config.get("startup_behavior", "last_note")
        idx = 1 if current_startup == "empty_note" else 0
        startup_dropdown.set_selected(idx)
        
        startup_dropdown.connect("notify::selected-item", self.on_startup_behavior_changed)
        startup_row.add_suffix(startup_dropdown)
        behavior_group.add(startup_row)

        confirm_row = Adw.ActionRow(
            title="Confirm Before Deleting",
            subtitle="Ask for confirmation when deleting a note",
        )
        confirm_switch = Gtk.Switch()
        confirm_switch.set_valign(Gtk.Align.CENTER)
        confirm_switch.set_active(config.get("confirm_delete", True))
        confirm_switch.connect("notify::active", self.on_confirm_delete_changed)
        confirm_row.add_suffix(confirm_switch)
        confirm_row.set_activatable_widget(confirm_switch)
        behavior_group.add(confirm_row)

        page.add(behavior_group)

        # Storage Group
        group = Adw.PreferencesGroup(title="Storage")
        
        row = Adw.ActionRow(title="Notes Directory", subtitle=str(DATA_DIR))
        
        btn = Gtk.Button(label="Change...")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", self.on_change_dir, row)
        row.add_suffix(btn)
        
        group.add(row)
        page.add(group)
        
        pref_window.add(page)
        pref_window.present()

    def on_font_changed(self, font_btn, param):
        desc = font_btn.get_font_desc()
        if desc:
            font_name = desc.to_string()
            config.set("font_name", font_name)
            self.apply_theme()

    def on_theme_snippet_toggled(self, snippet):
        if snippet.get_active():
            old_theme = config.get("paper_theme", "blank")
            theme_id = snippet.theme_id
            config.set("paper_theme", theme_id)
            
            # Update all open editors
            for i in range(self.carousel.get_n_pages()):
                editor = self.carousel.get_nth_page(i)
                editor.textview.remove_css_class(f"paper-{old_theme}")
                editor.textview.add_css_class(f"paper-{theme_id}")

    def on_spacing_changed(self, dropdown, param):
        selected = dropdown.get_selected_item()
        if selected:
            spacing = selected.get_string()
            config.set("line_spacing", spacing)
            self.update_line_spacing()

    def on_confirm_delete_changed(self, switch, param):
        config.set("confirm_delete", switch.get_active())

    def on_startup_behavior_changed(self, dropdown, param):
        selected = dropdown.get_selected()
        val = "empty_note" if selected == 1 else "last_note"
        config.set("startup_behavior", val)

    def update_line_spacing(self):
        spacing_str = config.get("line_spacing", "1.2")
        try:
            spacing_val = float(spacing_str)
        except ValueError:
            spacing_val = 1.2
            
        # Convert multiplier to rough pixels (assuming ~16px font size)
        # Normal (1.0) = 0px
        # Relaxed (1.2) = 3px above/below
        # Loose (1.5) = 8px above/below
        # Very Loose (2.0) = 16px above/below
        extra_pixels = int((spacing_val - 1.0) * 16)
        above_below = max(0, extra_pixels // 2)
        inside_wrap = max(0, extra_pixels)
        
        for i in range(self.carousel.get_n_pages()):
            editor = self.carousel.get_nth_page(i)
            editor.textview.set_pixels_above_lines(above_below)
            editor.textview.set_pixels_below_lines(above_below)
            editor.textview.set_pixels_inside_wrap(inside_wrap)

    def on_change_dir(self, btn, row):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Notes Directory")
        dialog.select_folder(self, None, self.on_folder_selected, row)

    def on_folder_selected(self, dialog, result, row):
        global DATA_DIR, TRASH_DIR
        try:
            folder = dialog.select_folder_finish(result)
            new_dir = Path(folder.get_path())
            if new_dir != DATA_DIR:
                config.data_dir = new_dir
                DATA_DIR = new_dir
                TRASH_DIR = DATA_DIR / ".trash"
                row.set_subtitle(str(DATA_DIR))
                
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                
                # Clear carousel and reload
                while self.carousel.get_n_pages() > 0:
                    self.carousel.remove(self.carousel.get_nth_page(0))
                self.load_notes()
        except GLib.Error:
            pass

    def on_pin_toggled(self, btn):
        self.set_keep_above(btn.get_active())

    def on_close_request(self, window):
        config.set("window_width", self.get_width())
        config.set("window_height", self.get_height())
        config.set("is_maximized", self.is_maximized())
        
        current_page_idx = int(round(self.carousel.get_position()))
        if current_page_idx < self.carousel.get_n_pages():
            editor = self.carousel.get_nth_page(current_page_idx)
            config.set("last_active_note", str(editor.file_path))
            
        return False

    def apply_theme(self):
        font_name = config.get("font_name")
        font_css = ""
        if font_name:
            font_desc = Pango.FontDescription.from_string(font_name)
            family = font_desc.get_family()
            size = font_desc.get_size() / Pango.SCALE
            font_css = f"font-family: '{family}'; font-size: {size}pt;"
            
        custom_css = f"""
        textview {{ {font_css} }}
        
        .theme-btn {{
            min-width: 48px;
            min-height: 48px;
            border-radius: 50%;
            border: 1px solid alpha(currentColor, 0.15);
            padding: 0;
            box-shadow: none;
        }}
        .theme-btn.system {{
            background: linear-gradient(135deg, #ffffff 49.5%, #242424 50.5%);
        }}
        .theme-btn.light {{
            background: #ffffff;
        }}
        .theme-btn.dark {{
            background: #242424;
        }}
        .theme-btn:checked {{
            border: 2px solid @accent_bg_color;
            box-shadow: inset 0 0 0 2px @window_bg_color;
        }}
        """
        try:
            self.css_provider.load_from_data(custom_css.encode('utf-8'))
        except GLib.Error:
            pass
