import re
import uuid
from pathlib import Path
from gi.repository import Gtk, GLib, Gdk
from whisp.config import config, DATA_DIR
from whisp.highlighter import MarkdownHighlighter

class NoteEditor(Gtk.Overlay):
    def __init__(self, file_path=None, on_title_changed=None):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        
        self.file_path = Path(file_path) if file_path else DATA_DIR / f"{uuid.uuid4().hex}.md"
        self.on_title_changed = on_title_changed
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_propagate_natural_width(False)
        self.set_child(self.scrolled)
        
        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_left_margin(32)
        self.textview.set_right_margin(32)
        self.textview.set_top_margin(32)
        self.textview.set_bottom_margin(32)
        self.textview.add_css_class(f"paper-{config.get('paper_theme', 'blank')}")
        self.scrolled.set_child(self.textview)
        
        self.buffer = self.textview.get_buffer()
        self.highlighter = MarkdownHighlighter(self.buffer)
        
        self.load_file()
        
        self.buffer.connect("changed", self.on_buffer_changed)
        self.save_timeout_id = 0
        
        # Add keyboard shortcuts (Capture phase for structural locks)
        key_ctrl_capture = Gtk.EventControllerKey()
        key_ctrl_capture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl_capture.connect("key-pressed", self.on_key_pressed_capture)
        self.textview.add_controller(key_ctrl_capture)
        
        # Add keyboard shortcuts (Bubble phase for normal shortcuts)
        key_ctrl_bubble = Gtk.EventControllerKey()
        key_ctrl_bubble.connect("key-pressed", self.on_key_pressed_bubble)
        self.textview.add_controller(key_ctrl_bubble)

    def on_buffer_changed(self, buffer):
        if self.save_timeout_id:
            GLib.source_remove(self.save_timeout_id)
        self.save_timeout_id = GLib.timeout_add(1000, self.save_file)
        
        if self.on_title_changed:
            self.on_title_changed(self)

    def on_key_pressed_capture(self, controller, keyval, keycode, state):
        if not self.buffer.get_has_selection():
            if keyval == Gdk.KEY_BackSpace:
                insert_mark = self.buffer.get_insert()
                cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
                line_start = cursor_iter.copy()
                line_start.set_line_offset(0)
                line_end = cursor_iter.copy()
                line_end.forward_to_line_end()
                
                text_before = self.buffer.get_text(line_start, cursor_iter, False)
                full_line = self.buffer.get_text(line_start, line_end, False)
                
                # Ctrl+Backspace safeguard
                if state & Gdk.ModifierType.CONTROL_MASK:
                    if cursor_iter.equal(line_start):
                        return True # Stop Ctrl+Backspace from eating the newline and going to previous line
                    if re.match(r'^(\s*[-*+]|\s*[☐☑])\s*$', text_before):
                        # If deleting word backward just after a bullet, delete the bullet but don't eat the newline above
                        self.buffer.delete(line_start, cursor_iter)
                        return True
                        
                # Normal Backspace on empty checkbox in list note
                elif not (state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.ALT_MASK)):
                    if self.is_list_note():
                        if re.match(r'^\s*[☐☑]\s*$', text_before):
                            if re.match(r'^\s*[☐☑]\s*$', full_line):
                                self.buffer.delete(line_start, line_end)
                                if line_start.backward_char() and line_start.get_char() == '\n':
                                    t = line_start.copy()
                                    t.forward_char()
            # Smart Checkbox Overwrite (# only)
            elif keyval == Gdk.KEY_numbersign:
                insert_mark = self.buffer.get_insert()
                cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
                line_start = cursor_iter.copy()
                line_start.set_line_offset(0)
                text_before = self.buffer.get_text(line_start, cursor_iter, False)
                
                if self.is_list_note() and re.match(r'^\s*[☐☑]\s*$', text_before):
                    self.buffer.delete(line_start, cursor_iter)
                    # Return False so GTK proceeds to insert the typed character natively
                    pass
                                
            if state & Gdk.ModifierType.CONTROL_MASK:
                if state & Gdk.ModifierType.SHIFT_MASK:
                    if keyval == Gdk.KEY_v or keyval == Gdk.KEY_V:
                        self.paste_plain_text()
                        return True
                    elif keyval == Gdk.KEY_l or keyval == Gdk.KEY_L:
                        self.shorten_link()
                        return True
                elif not (state & (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.ALT_MASK)):
                    if keyval == Gdk.KEY_v or keyval == Gdk.KEY_V:
                        self.handle_smart_paste()
                        return True
                        
        return False

    def on_key_pressed_bubble(self, controller, keyval, keycode, state):
        if state & Gdk.ModifierType.CONTROL_MASK:
            if state & Gdk.ModifierType.SHIFT_MASK:
                if keyval == Gdk.KEY_c or keyval == Gdk.KEY_C:
                    self.buffer.insert_at_cursor("- [ ] ")
                    return True
                    
            if keyval == Gdk.KEY_b or keyval == Gdk.KEY_B:
                self.wrap_text("**", "**", "bold")
                return True
            elif keyval == Gdk.KEY_i or keyval == Gdk.KEY_I:
                self.wrap_text("*", "*", "italic")
                return True
            elif keyval == Gdk.KEY_u or keyval == Gdk.KEY_U:
                self.wrap_text("<u>", "</u>", "underline")
                return True
            elif keyval == Gdk.KEY_s or keyval == Gdk.KEY_S:
                self.toggle_checkbox()
                return True
                
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            if not (state & Gdk.ModifierType.SHIFT_MASK):
                return self.handle_return()
            
        if keyval in (Gdk.KEY_Tab, Gdk.KEY_KP_Tab, Gdk.KEY_ISO_Left_Tab):
            if (state & Gdk.ModifierType.SHIFT_MASK) or keyval == Gdk.KEY_ISO_Left_Tab or (state & Gdk.ModifierType.CONTROL_MASK):
                return self.handle_shift_tab()
            else:
                return self.handle_tab()
            
        return False

    def handle_tab(self):
        insert_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
        line_start = cursor_iter.copy()
        line_start.set_line_offset(0)
        
        # Get current line text to find its indent
        line_end = cursor_iter.copy()
        line_end.forward_to_line_end()
        current_text = self.buffer.get_text(line_start, line_end, False)
        m_curr = re.match(r'^(\s*)', current_text)
        curr_indent_len = len(m_curr.group(1)) if m_curr else 0
        
        # Check previous line
        prev_line_iter = line_start.copy()
        if not prev_line_iter.backward_line():
            return True # First line, no indentation allowed
            
        prev_line_end = prev_line_iter.copy()
        prev_line_end.forward_to_line_end()
        prev_text = self.buffer.get_text(prev_line_iter, prev_line_end, False)
        
        # Ignore empty previous lines for indentation calculation? 
        # Actually, standard markdown usually bases it on the previous item.
        m_prev = re.match(r'^(\s*)', prev_text)
        prev_indent_len = len(m_prev.group(1)) if m_prev else 0
        
        if curr_indent_len >= prev_indent_len + 4:
            return True # Already indented 1 level deeper than the previous line
            
        self.buffer.insert(line_start, "    ")
        self.recalculate_list_number(line_start)
        return True

    def handle_shift_tab(self):
        insert_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
        line_start = cursor_iter.copy()
        line_start.set_line_offset(0)
        
        check_iter = line_start.copy()
        check_iter.forward_chars(4)
        text = self.buffer.get_text(line_start, check_iter, False)
        
        spaces_to_remove = 0
        for char in text:
            if char == ' ':
                spaces_to_remove += 1
            else:
                break
                
        if spaces_to_remove > 0:
            del_iter = line_start.copy()
            del_iter.forward_chars(spaces_to_remove)
            self.buffer.delete(line_start, del_iter)
            self.recalculate_list_number(line_start)
            return True
        return False

    def recalculate_list_number(self, line_start_iter):
        line_start = line_start_iter.copy()
        line_start.set_line_offset(0)
        line_end = line_start.copy()
        line_end.forward_to_line_end()
        text = self.buffer.get_text(line_start, line_end, False)
        
        m_ol = re.match(r'^(\s*)(\d+)\.(\s+.*)$', text)
        if not m_ol:
            return
            
        current_indent_len = len(m_ol.group(1))
        
        search_iter = line_start.copy()
        prev_num = 0
        while search_iter.backward_line():
            s_end = search_iter.copy()
            s_end.forward_to_line_end()
            s_text = self.buffer.get_text(search_iter, s_end, False)
            
            if not s_text.strip():
                continue
            
            m_search = re.match(r'^(\s*)(\d+)\.\s+.*$', s_text)
            if m_search:
                s_indent_len = len(m_search.group(1))
                if s_indent_len == current_indent_len:
                    prev_num = int(m_search.group(2))
                    break
                elif s_indent_len < current_indent_len:
                    break
            else:
                m_other = re.match(r'^(\s*)', s_text)
                if m_other and len(m_other.group(1)) < current_indent_len:
                    break
                    
        new_num = prev_num + 1
        current_num_str = m_ol.group(2)
        new_num_str = str(new_num)
        
        if current_num_str != new_num_str:
            num_start = line_start.copy()
            num_start.forward_chars(current_indent_len)
            num_end = num_start.copy()
            num_end.forward_chars(len(current_num_str))
            
            self.buffer.delete(num_start, num_end)
            self.buffer.insert(num_start, new_num_str)

    def toggle_checkbox(self):
        insert_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
        line_start = cursor_iter.copy()
        line_start.set_line_offset(0)
        line_end = cursor_iter.copy()
        line_end.forward_to_line_end()
        line_text = self.buffer.get_text(line_start, line_end, False)
        
        m_box = re.match(r'^(\s*)([☐☑])\s*', line_text)
        if m_box:
            # Toggle it
            box_offset = len(m_box.group(1))
            box_iter = line_start.copy()
            box_iter.forward_chars(box_offset)
            box_end = box_iter.copy()
            box_end.forward_chars(1)
            current_box = self.buffer.get_text(box_iter, box_end, False)
            new_box = "☑" if current_box == "☐" else "☐"
            self.buffer.delete(box_iter, box_end)
            self.buffer.insert(box_iter, new_box)
            return True
            
        # If it's a bullet, replace bullet with checkbox
        m_bullet = re.match(r'^(\s*)([-*+])\s+', line_text)
        if m_bullet:
            b_offset = len(m_bullet.group(1))
            b_iter = line_start.copy()
            b_iter.forward_chars(b_offset)
            b_end = b_iter.copy()
            b_end.forward_chars(len(m_bullet.group(2)))
            self.buffer.delete(b_iter, b_end)
            self.buffer.insert(b_iter, "☐")
            return True
            
        # Otherwise, prepend checkbox after indent
        m_indent = re.match(r'^(\s*)', line_text)
        indent_len = len(m_indent.group(1)) if m_indent else 0
        ins_iter = line_start.copy()
        ins_iter.forward_chars(indent_len)
        self.buffer.insert(ins_iter, "☐ ")
        return True

    def count_checkboxes(self):
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, False)
        return len(re.findall(r'^(\s*)[☐☑]', text, re.MULTILINE))

    def is_empty(self):
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, False).strip()
        return len(text) == 0 or bool(re.match(r'^(#{1,6}\s*)?list(\s*[:\s].*)?$', text.lower()))

    def is_list_note(self):
        start_iter = self.buffer.get_start_iter()
        end_iter = start_iter.copy()
        end_iter.forward_to_line_end()
        first_line = self.buffer.get_text(start_iter, end_iter, False).strip().lower()
        return bool(re.match(r'^(#{1,6}\s*)?list(\s*[:\s].*)?$', first_line))

    def handle_return(self):
        insert_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
        
        line_start = cursor_iter.copy()
        line_start.set_line_offset(0)
        line_text = self.buffer.get_text(line_start, cursor_iter, False)
        
        is_list = self.is_list_note()

        def insert_sync(text):
            self.buffer.insert_at_cursor(text)
            GLib.idle_add(lambda: self.textview.scroll_mark_onscreen(self.buffer.get_insert()) or False)
            return True

        if is_list:
            # Empty checkbox
            m_empty = re.match(r'^(\s*)[☐☑]\s*$', line_text)
            if m_empty:
                # Delete the entire line
                line_end = cursor_iter.copy()
                line_end.forward_to_line_end()
                self.buffer.delete(line_start, line_end)
                
                # Delete the preceding newline so we don't leave an empty line
                if line_start.backward_char() and line_start.get_char() == '\n':
                    tmp = line_start.copy()
                    tmp.forward_char()
                    self.buffer.delete(line_start, tmp)
                    
                GLib.idle_add(lambda: self.textview.scroll_mark_onscreen(self.buffer.get_insert()) or False)
                return True
                
            m_indent = re.match(r'^(\s*)', line_text)
            indent = m_indent.group(1) if m_indent else ""
            return insert_sync(f"\n{indent}☐ ")

        # Check if current line is an empty checkbox
        m_empty = re.match(r'^(\s*)[☐☑]\s*$', line_text)
        if m_empty:
            self.buffer.delete(line_start, cursor_iter)
            return insert_sync("\n")
            
        # Check if current line is a checkbox
        m_box = re.match(r'^(\s*)([☐☑])\s+(.*)$', line_text)
        if m_box:
            indent, box, content = m_box.groups()
            return insert_sync(f"\n{indent}☐ ")
        
        # Match unordered lists (- or *)
        m_ul = re.match(r'^(\s*)([-*+])\s+(.*)$', line_text)
        if m_ul:
            indent, bullet, content = m_ul.groups()
            if not content.strip():
                self.buffer.delete(line_start, cursor_iter)
                return insert_sync("\n")
            else:
                return insert_sync(f"\n{indent}{bullet} ")
                
        # Match ordered lists (1., 2., etc)
        m_ol = re.match(r'^(\s*)(\d+)\.\s+(.*)$', line_text)
        if m_ol:
            indent, num, content = m_ol.groups()
            if not content.strip():
                self.buffer.delete(line_start, cursor_iter)
                return insert_sync("\n")
            else:
                next_num = int(num) + 1
                return insert_sync(f"\n{indent}{next_num}. ")
                
        return False

    def wrap_text(self, prefix, suffix, default_text):
        bounds = self.buffer.get_selection_bounds()
        if not bounds:
            insert_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            
            check_start = insert_iter.copy()
            check_start.backward_chars(len(prefix))
            check_end = insert_iter.copy()
            check_end.forward_chars(len(suffix))
            
            text_before = self.buffer.get_text(check_start, insert_iter, False)
            text_after = self.buffer.get_text(insert_iter, check_end, False)
            
            if text_before == prefix and text_after == suffix:
                self.buffer.delete(check_start, check_end)
                return
                
            if text_after == suffix:
                insert_iter.forward_chars(len(suffix))
                self.buffer.place_cursor(insert_iter)
                return
                
            self.buffer.insert(insert_iter, prefix + suffix)
            insert_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            insert_iter.backward_chars(len(suffix))
            self.buffer.place_cursor(insert_iter)
            return
            
        start, end = bounds
        text = self.buffer.get_text(start, end, False)
        self.buffer.delete(start, end)
        
        start = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        
        # Check if the text is already wrapped
        if text.startswith(prefix) and text.endswith(suffix) and len(text) >= len(prefix) + len(suffix):
            # Toggle off (unwrap)
            new_text = text[len(prefix):-len(suffix)]
        else:
            # Toggle on (wrap)
            new_text = f"{prefix}{text}{suffix}"
            
        self.buffer.insert(start, new_text)
        
        # Re-select the newly modified text
        insert_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        insert_iter.backward_chars(len(new_text))
        bound_iter = insert_iter.copy()
        bound_iter.forward_chars(len(new_text))
        self.buffer.select_range(insert_iter, bound_iter)

    def handle_smart_paste(self):
        clipboard = self.textview.get_clipboard()
        clipboard.read_text_async(None, self.on_smart_paste_read)

    def on_smart_paste_read(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if text:
                url = text.strip()
                if re.match(r'^https?://[^\s]+$', url) and len(url) > 30:
                    display_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
                    if len(display_url) > 25:
                        display_url = display_url[:25] + "..."
                    markdown_link = f"[{display_url}]({url})"
                    GLib.idle_add(lambda: self.buffer.insert_at_cursor(markdown_link) or False)
                else:
                    GLib.idle_add(lambda: self.buffer.insert_at_cursor(text) or False)
        except GLib.Error:
            pass

    def paste_plain_text(self):
        clipboard = self.textview.get_clipboard()
        clipboard.read_text_async(None, self.on_clipboard_read)

    def on_clipboard_read(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if text:
                # Strip markdown syntax for plain text paste
                text = re.sub(r'#{1,6}\s+', '', text)
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
                text = re.sub(r'(?<!\*)\*(.*?)\*(?!\*)', r'\1', text)
                text = re.sub(r'__(.*?)__', r'\1', text)
                text = re.sub(r'(?<!_)_(.*?)_(?!_)', r'\1', text)
                text = re.sub(r'`(.*?)`', r'\1', text)
                text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
                text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
                text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
                text = re.sub(r'^\s*[☐☑]\s*', '', text, flags=re.MULTILINE)
                
                GLib.idle_add(lambda: self.buffer.insert_at_cursor(text) or False)
        except GLib.Error:
            pass

    def shorten_link(self):
        bounds = self.buffer.get_selection_bounds()
        start = end = None
        url = ""
        
        if bounds:
            start, end = bounds
            url = self.buffer.get_text(start, end, False).strip()
        else:
            # Grab word under cursor
            insert_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            start = insert_iter.copy()
            end = insert_iter.copy()
            
            # Move start to beginning of word (or non-whitespace)
            while start.backward_char():
                if start.get_char() in (' ', '\n', '\t'):
                    start.forward_char()
                    break
                    
            # Move end to end of word
            while end.forward_char():
                if end.get_char() in (' ', '\n', '\t'):
                    break
                    
            url = self.buffer.get_text(start, end, False).strip()
            
        if re.match(r'^https?://[^\s]+$', url) and len(url) > 30:
            display_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
            if len(display_url) > 25:
                display_url = display_url[:25] + "..."
            markdown_link = f"[{display_url}]({url})"
            
            start_mark = self.buffer.create_mark(None, start, True)
            end_mark = self.buffer.create_mark(None, end, False)
            GLib.idle_add(self.replace_mark_range, start_mark, end_mark, markdown_link)

    def replace_mark_range(self, start_mark, end_mark, new_text):
        start = self.buffer.get_iter_at_mark(start_mark)
        end = self.buffer.get_iter_at_mark(end_mark)
        self.buffer.delete(start, end)
        self.buffer.insert(start, new_text)
        self.buffer.delete_mark(start_mark)
        self.buffer.delete_mark(end_mark)
        return False

    def load_file(self):
        if self.file_path.exists():
            content = self.file_path.read_text(encoding='utf-8')
            self.buffer.set_text(content)
            self.highlighter.highlight()

    def save_file(self):
        self.save_timeout_id = 0
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, True)
        self.file_path.write_text(text, encoding='utf-8')
        return False

    def get_title(self, max_length=50):
        start, end = self.buffer.get_bounds()
        text = self.buffer.get_text(start, end, True)
        first_line = text.split('\n')[0].strip() if text else ""
        first_line = re.sub(r'^#+\s*', '', first_line)
        if first_line and len(first_line) > max_length:
            first_line = first_line[:max_length].rstrip() + "…"
        return first_line if first_line else "New Note"
