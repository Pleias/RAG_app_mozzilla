import json
import os
import sys
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QGridLayout, QLabel, QListView
from PySide6.QtGui import QStandardItem, QStandardItemModel
from dialog_display import ChatDialog
from ui_froms.ui_main_window import Ui_MainWindow
from ui_froms.reference_ui import Ui_Form as ReferenceForm
from connect_db import ConnectDB
from file_management_window import FileManagementWindow  # Import the file management window

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit
from PySide6.QtGui import QIcon
from get_answer_from_api import get_response


class ReferenceWidget(QWidget):
    def __init__(self, text):
        super().__init__()

        # Initialize of the main window
        self.ui = ReferenceForm()
        self.ui.setupUi(self)
        self.ui.label_2.setText(text)


class CustomWidget(QWidget):
    """
    create chat in chats list
    """

    def __init__(self, text, show_btn_flag, *args, **kwargs):
        super(CustomWidget, self).__init__(*args, **kwargs)
        # Create layout for chat title
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)

        # create icon widget of chat title
        chat_icon = QIcon("static/icons/icons8-chat-96.png")
        chat_icon_btn = QPushButton(self)
        chat_icon_btn.setIcon(chat_icon)

        # Create title widget to show title
        chat_title = QLineEdit(self)
        chat_title.setText(text)
        chat_title.setReadOnly(True)

        # Create delete and edit button for chat title
        delete_btn = QPushButton(self)
        delete_btn.setIcon(QIcon("static/icons/icons8-delete-32.png"))

        edit_btn = QPushButton(self)
        edit_btn.setIcon(QIcon("static/icons/icons8-edit-32.png"))

        # StyleSheet for QPushButton in chat title
        style_str = """
            QPushButton {
                border: none;
                max-width: 20px;
                max-height: 20px;
                background:transparent;
            }
        """
        # StyleSheet for QLineEdit in chat title
        chat_title_style = """
            QLineEdit {
                background:transparent;
                border: none;
                color: #261f1e;
                font-size: 15px;
                padding-left: 2px;
            }
        """
        chat_title.setStyleSheet(chat_title_style)
        chat_icon_btn.setStyleSheet(style_str)
        edit_btn.setStyleSheet(style_str)
        delete_btn.setStyleSheet(style_str)

        if not show_btn_flag:
            # If not be selected, hide delete and edit button in chat title list
            delete_btn.hide()
            edit_btn.hide()

        # Add all the widgets of the chat title.
        layout.addWidget(chat_icon_btn)
        layout.addWidget(chat_title)
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize of the main window
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Instantiate the database object
        self.connect_db = ConnectDB()
        
        # Initialize file management window but keep it hidden
        self.file_management_window = None

        # Connect the Library button to open the file management window
        self.ui.pushButton_3.clicked.connect(self.open_file_management_window)

        # Get objects from main window
        self.message_input = self.ui.input_textEdit_2
        self.input_frame = self.ui.input_frame_2
        self.new_chat_btn = self.ui.new_chat_btn
        self.send_message_btn = self.ui.send_btn_2
        self.main_scrollArea = self.ui.scrollArea_2
        self.robot_combo_box = self.ui.comboBox_2
        self.clear_conversations_btn = self.ui.pushButton_9
        self.logout_btn = self.ui.pushButton_6
        self.ui.chat_list.clicked.connect(self.on_chat_list_clicked)

        # Hide scrollbar of scroll area
        self.main_scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Resize input frame and textEdit
        self.message_input.setFixedHeight(24)
        self.input_frame.setFixedHeight(42)

        # Set data for main chat and chat list when start app
        self.show_chat_list()

        # Set signal and slot
        self.send_message_btn.clicked.connect(self.get_response)
        self.new_chat_btn.clicked.connect(self.create_new_chat)
        self.clear_conversations_btn.clicked.connect(self.clear_conversations)
        self.logout_btn.clicked.connect(self.log_out)

    ## Functions for main window //////////////////////
    # Create a new chat
    def create_new_chat(self):
        self.clear_main_scroll_area()
        self.show_chat_list(selected_index=None)

    # Delete all the chats from chat list
    def clear_conversations(self):
        self.connect_db.delete_all_data()
        self.clear_main_scroll_area()
        self.show_chat_list()

    # Logout application
    def log_out(self):
        self.close()

    # Adjust input height by text height
    def on_input_textEdit_textChanged(self):
        document = self.message_input.document()
        self.message_input.setFixedHeight(int(document.size().height()))
        self.input_frame.setFixedHeight(int(document.size().height() + 18))

    ## Functions for chat list ///////////////////////////////
    # Delete a chat from chat list
    def delete_chat_data(self):
        # Get current selected chat index
        selected_chat_index = self.ui.chat_list.currentIndex()
        index = selected_chat_index.row()
        self.connect_db.delete_chat_data(index)
        self.show_chat_list()

    # Function for clearing all the widgets in chat window when reload chat window
    def clear_main_scroll_area(self):
        # Get QGridLayout object from scroll area
        grid_layout = self.main_scrollArea.findChild(QGridLayout)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Get all the objects in main chat window
        children_list = grid_layout.children()
        remove_widget_list = [QLabel, QPushButton]
        for remove_widget in remove_widget_list:
            children_list += self.main_scrollArea.findChildren(remove_widget)

        # Delete all the found object
        for child in children_list:
            child.deleteLater()

        # Remove all the spacer items from the grid layout
        for row in range(grid_layout.rowCount()):
            for column in range(grid_layout.columnCount()):
                item = grid_layout.itemAtPosition(row, column)
                if item:
                    grid_layout.removeItem(item)

        return grid_layout

    # Signal and slot function for chat list(QListView)
    def on_chat_list_clicked(self):
        chat_list = []

        # Clear input when change chat
        self.message_input.clear()
        # Get select row
        current_index = self.ui.chat_list.currentIndex()
        select_row = current_index.row()

        # Get the count of chat list
        chat_models = self.ui.chat_list.model()
        chat_count = chat_models.rowCount()

        # Traverse chat list in window
        for i in range(chat_count):
            row_index = chat_models.index(i, 0)
            current_chat = self.ui.chat_list.indexWidget(row_index)
            chat_title = current_chat.findChild(QLineEdit)
            if chat_title:
                # Check if the chat state is waiting to delete
                if i == select_row and chat_title.text().startswith("Delete \""):
                    chat_list.append(chat_title.text().split('"')[1])
                else:
                    chat_list.append(chat_title.text())
            else:
                chat_list.append("")

        # Reload chat list
        for row, chat in enumerate(chat_list):
            index = chat_models.index(row, 0)
            # Check if the chat title is selected?
            if row == select_row:
                show_btn_flag = True
            else:
                show_btn_flag = False

            # Create chat title widget
            widget = CustomWidget(chat, show_btn_flag)

            # Set and show chat title in chat list(QListView)
            self.ui.chat_list.setIndexWidget(index, widget)

            # Get QPushButton object in  chat title widget
            operation_btn = widget.findChildren(QPushButton)
            # Connect signal and slot for buttons
            edit_btn = operation_btn[2]
            edit_btn.clicked.connect(self.edit_chat)

            delete_btn = operation_btn[1]
            delete_btn.clicked.connect(self.delete_chat)

        # Get the selected chat data and show it in main chat content window
        chat_db = self.connect_db.get_chat_data()
        chat_data = chat_db[select_row]
        self.show_chat_window(chat_data)

    @Slot()
    def edit_chat(self):
        current_index = self.ui.chat_list.currentIndex()
        current_chat = self.ui.chat_list.indexWidget(current_index)

        chat_title = current_chat.findChild(QLineEdit)

        # Get original chat title
        pre_chat_title = chat_title.text()

        chat_title.setReadOnly(False)
        chat_title_style = """
            QLineEdit {
                background:transparent;
                border: 1px solid #2563eb;
                color: #fff;
                font-size: 15px;
                padding-left: 2px;
            }
        """

        chat_title.setStyleSheet(chat_title_style)

        operation_btns = current_chat.findChildren(QPushButton)
        confirm_btn = operation_btns[2]
        cancel_btn = operation_btns[1]

        confirm_btn.setIcon(QIcon("static/icons/check-lg.svg"))
        cancel_btn.setIcon(QIcon("static/icons/x-lg.svg"))

        confirm_btn.clicked.disconnect()
        cancel_btn.clicked.disconnect()

        confirm_btn.clicked.connect(lambda: self.confirm_edit(chat_title))
        cancel_btn.clicked.connect(lambda: self.cancel_edit(pre_chat_title, chat_title))

    @Slot()
    def confirm_edit(self, chat_title):
        current_index = self.ui.chat_list.currentIndex().row()

        chat_db = self.connect_db.get_chat_data()
        chat_db[current_index]["title"] = chat_title.text()

        self.connect_db.save_chat_data(chat_db)
        self.on_chat_list_clicked()

    @Slot()
    def cancel_edit(self, pre_chat_title, chat_title):
        chat_title.setText(pre_chat_title)
        self.on_chat_list_clicked()

    @Slot()
    def delete_chat(self):
        current_index = self.ui.chat_list.currentIndex()
        current_chat = self.ui.chat_list.indexWidget(current_index)

        chat_title = current_chat.findChild(QLineEdit)
        chat_title.setReadOnly(True)
        chat_title_text = chat_title.text()
        chat_title.setText(f'Delete "{chat_title_text}"?')
        chat_title_style = """
            QLineEdit {
                background:transparent;
                border: none;
                color: #fff;
                font-size: 15px;
                padding-left: 2px;
            }
        """

        chat_title.setStyleSheet(chat_title_style)

        operation_btns = current_chat.findChildren(QPushButton)
        chat_icon_btn = operation_btns[0]
        confirm_btn = operation_btns[2]
        cancel_btn = operation_btns[1]

        chat_icon_btn.setIcon(QIcon("static/icons/delete.svg"))
        confirm_btn.setIcon(QIcon("static/icons/check-lg.svg"))
        cancel_btn.setIcon(QIcon("static/icons/x-lg.svg"))

        confirm_btn.clicked.disconnect()
        cancel_btn.clicked.disconnect()

        confirm_btn.clicked.connect(self.confirm_delete)
        cancel_btn.clicked.connect(self.cancel_delete)

    @Slot()
    def confirm_delete(self):
        current_index = self.ui.chat_list.currentIndex()
        index = current_index.row()
        chat_db = self.connect_db.get_chat_data()
        chat_db.pop(index)

        self.connect_db.save_chat_data(chat_db)
        self.show_home_window()
        self.show_chat_list()

    @Slot()
    def cancel_delete(self):
        self.on_chat_list_clicked()

    # Show one chat data in main chat content window
    def show_chat_window(self, chat_data):
        grid_layout = self.clear_main_scroll_area()
        dialog = ChatDialog(chat_data)
        grid_layout.addWidget(dialog)

    def show_chat_list(self, selected_index=None):
        # Create QStandardItemModel for show chat title list
        model = QStandardItemModel()
        self.ui.chat_list.setModel(model)
        # Get chat title list from database
        chat_list = self.connect_db.get_chat_title_list()

        for chat in chat_list:
            item = QStandardItem()
            model.appendRow(item)

            index = item.index()
            index_text = index.row()

            if index_text == selected_index:
                show_btn_flag = True
                # Set current item selected
                self.ui.chat_list.setCurrentIndex(index)
            else:
                show_btn_flag = False

            # Create chat title widget
            widget = CustomWidget(chat, show_btn_flag)

            # Set and show chat title in chat list(QListView)
            self.ui.chat_list.setIndexWidget(index, widget)

            # Get QPushButton object in  chat title widget
            operation_btn = widget.findChildren(QPushButton)

            # Connect signal and slot for buttons
            edit_btn = operation_btn[2]
            edit_btn.clicked.connect(self.edit_chat)

            delete_btn = operation_btn[1]
            delete_btn.clicked.connect(self.delete_chat)

    def show_reference_list(self, chat_list, selected_index):
        # Create QStandardItemModel for show chat title list
        model = QStandardItemModel()
        self.ui.chat_list_2.setModel(model)
        # Get chat title list from database
        for chat in chat_list:
            item = QStandardItem()
            model.appendRow(item)

            index = item.index()
            index_text = index.row()

            widget = ReferenceWidget(chat)
            self.ui.chat_list_2.setIndexWidget(index, widget)

        # Set spacing and margins
        self.ui.chat_list_2.setSpacing(10)
        self.ui.chat_list_2.setContentsMargins(5, 0, 5, 5)
        # self.ui.chat_list_2.setViewMode(QListView.IconMode)

    # Get response from the api and show it
    def get_response(self):
        message_input = self.message_input.toPlainText().strip()

        chat_db = self.connect_db.get_chat_data()

        if message_input:
            source_documents, response_str = get_response(message_input, debug=False)
            source_documents.append("attention is all you need.pdf")
            # Check if open a chat
            if self.ui.chat_list.selectedIndexes():
                # Get current selected chat index
                current_index = self.ui.chat_list.currentIndex()
                select_row = current_index.row()

                chat_db[select_row]["chat_list"] += [{"input_str": message_input, "out_str": response_str}]
                chat_data = chat_db[select_row]

                self.connect_db.save_chat_data(chat_db)
                self.show_chat_window(chat_data)
                self.show_reference_list(source_documents, selected_index=0)

            else:
                # Create new chat and save it into database
                chat_data = {
                    "title": message_input,
                    "chat_list": [
                        {
                            "input_str": message_input,
                            "out_str": response_str
                        }
                    ]
                }
                chat_db.insert(0, chat_data)
                self.connect_db.save_chat_data(chat_db)

                # Reload window
                self.show_chat_window(chat_data)
                self.show_reference_list(source_documents, selected_index=0)
                self.show_chat_list(selected_index=0)

            ## Clear input after get response
            self.message_input.clear()
            return
    
    ## Functions for chat list ///////////////////////////////
    def open_file_management_window(self):
        # Create and show the file management window if not already open
        if self.file_management_window is None:
            self.file_management_window = FileManagementWindow()
        self.file_management_window.show()


if __name__ == "__main__":

    flag = os.path.exists("data/data.json")
    print(flag)

    if not flag:
        os.mkdir("data")
        with open("data/data.json", "w") as f:
            f.write(json.dumps([]))

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
