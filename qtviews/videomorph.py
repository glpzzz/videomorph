# -*- coding: utf-8 -*-
#
# File name: videomorph.py
#
#   VideoMorph - A PyQt5 frontend to ffmpeg.
#   Copyright 2016-2018 VideoMorph Development Team

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""This module defines the VideoMorph main window that holds the UI."""

from collections import OrderedDict
from functools import partial
from os.path import join as join_path
from os.path import dirname
from os.path import exists
from os.path import isdir
from os.path import isfile

from PyQt5.QtCore import (QSize,
                          Qt,
                          QSettings,
                          QDir,
                          QPoint,
                          QProcess)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (QMainWindow,
                             QWidget,
                             QVBoxLayout,
                             QHBoxLayout,
                             QSizePolicy,
                             QGroupBox,
                             QLabel,
                             QSpacerItem,
                             QComboBox,
                             QCheckBox,
                             QProgressBar,
                             QSystemTrayIcon,
                             QMenu,
                             QToolBar,
                             QTableWidgetItem,
                             QLineEdit,
                             QAction,
                             QAbstractItemView,
                             QFileDialog,
                             QMessageBox,
                             QProgressDialog,
                             QToolButton,
                             qApp)



from videomorph import APP_NAME
from videomorph import BASE_DIR
from videomorph import LOCALE
from videomorph import STATUS
from videomorph import SYS_PATHS
from videomorph import VERSION
from videomorph import VIDEO_FILTERS
from videomorph import VM_PATHS
from videomorph.console import search_directory_recursively
from videomorph.conversionlib import ConversionLib
from videomorph.media import MediaList
from videomorph.platformdeps import PlayerNotFoundError
from videomorph.platformdeps import launcher_factory
from videomorph.profile import ConversionProfile
from videomorph.utils import write_time
from . import COLUMNS
from . import videomorph_qrc
from .vmwidgets import TasksListTable
from .addprofile import AddProfileDialog
from .info import InfoDialog


class VideoMorphMW(QMainWindow):
    """VideoMorph Main Window class."""

    def __init__(self, controller):
        """Class initializer."""
        super(VideoMorphMW, self).__init__()
        self.controller = controller
        self.media_list_duration = 0.0

        # Window size
        self.resize(680, 576)
        # Set window title
        self._set_window_title()
        # Define and set app icon
        icon = QIcon()
        icon.addPixmap(QPixmap(':/icons/videomorph.ico'))
        self.setWindowIcon(icon)
        # Define app central widget
        self.central_widget = QWidget(self)

        self.vertical_layout = QVBoxLayout(self.central_widget)
        self.horizontal_layout = QHBoxLayout()
        self.vertical_layout_1 = QVBoxLayout()
        self.vertical_layout_2 = QVBoxLayout()

        self._group_settings()
        self._fix_layout()
        self._group_tasks_list()
        self._group_output_directory()
        self._group_progress()

        self.horizontal_layout.addLayout(self.vertical_layout_2)
        self.vertical_layout.addLayout(self.horizontal_layout)

        self.setCentralWidget(self.central_widget)

        self.source_dir = QDir.homePath()

        self._create_actions()

        # Tray Icon
        self._create_sys_tray_icon(icon)

        # Conversion library
        self.no_library_msg = self.tr('Ffmpeg Library not Found'
                                      ' in your System')
        self.conversion_lib = ConversionLib()
        self.conversion_lib.setup_converter(
            reader=self._ready_read,
            finisher=self._finish_file_encoding,
            process_channel=QProcess.MergedChannels)
        self.reader = self.conversion_lib.reader
        self.timer = self.conversion_lib.timer

        self._create_initial_settings()

        self.profile = ConversionProfile(
            prober=self.conversion_lib.prober_path)

        self.media_list = MediaList(profile=self.profile)

        self.populate_profiles_combo()

        self._read_app_settings()

        self._create_main_menu()

        self._create_context_menu()

        self._create_toolbar()

        self._create_status_bar()

        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self._update_ui_when_no_file()

    def _create_sys_tray_icon(self, icon):
        self.tray_icon_menu = QMenu(self)
        self.tray_icon_menu.addAction(self.open_media_file_action)
        self.tray_icon_menu.addAction(self.open_media_dir_action)
        self.tray_icon_menu.addSeparator()
        self.tray_icon_menu.addAction(self.clear_media_list_action)
        self.tray_icon_menu.addSeparator()
        self.tray_icon_menu.addAction(self.convert_action)
        self.tray_icon_menu.addAction(self.stop_all_action)
        self.tray_icon_menu.addSeparator()
        self.tray_icon_menu.addAction(self.exit_action)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setContextMenu(self.tray_icon_menu)

        self.tray_icon.show()

    def _group_settings(self):
        """Settings group."""
        gb_settings = QGroupBox(self.central_widget)
        gb_settings.setTitle(self.tr('Conversion Profile'))
        size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            gb_settings.sizePolicy().hasHeightForWidth())
        gb_settings.setSizePolicy(size_policy)
        horizontal_layout = QHBoxLayout(gb_settings)
        vertical_layout = QVBoxLayout()
        horizontal_layout_1 = QHBoxLayout()
        label_convert = QLabel(self.tr('Convert to:'))
        horizontal_layout_1.addWidget(label_convert)
        spacer_item = QSpacerItem(40,
                                  20,
                                  QSizePolicy.Expanding,
                                  QSizePolicy.Minimum)
        horizontal_layout_1.addItem(spacer_item)
        vertical_layout.addLayout(horizontal_layout_1)
        profile_tip = self.tr('Select a Video Format')
        self.cb_profiles = QComboBox(gb_settings,
                                     statusTip=profile_tip,
                                     toolTip=profile_tip)
        self.cb_profiles.setMinimumSize(QSize(200, 0))
        self.cb_profiles.setIconSize(QSize(22, 22))
        vertical_layout.addWidget(self.cb_profiles)
        horizontal_layout_2 = QHBoxLayout()
        label_quality = QLabel(self.tr('Target Quality:'))
        horizontal_layout_2.addWidget(label_quality)
        spacer_item_1 = QSpacerItem(40, 20,
                                    QSizePolicy.Expanding,
                                    QSizePolicy.Minimum)
        horizontal_layout_2.addItem(spacer_item_1)
        vertical_layout.addLayout(horizontal_layout_2)
        preset_tip = self.tr('Select a Video Target Quality')
        self.cb_quality = QComboBox(gb_settings,
                                    statusTip=preset_tip,
                                    toolTip=preset_tip)
        self.cb_quality.setMinimumSize(QSize(200, 0))

        self.cb_profiles.currentIndexChanged.connect(partial(
            self.populate_quality_combo, self.cb_quality))

        self.cb_quality.activated.connect(self._update_media_files_status)

        vertical_layout.addWidget(self.cb_quality)
        self.label_other_options = QLabel(self.tr('Other Options:'))
        sub_tip = self.tr('Insert Subtitles if Available in Source Directory')
        self.chb_subtitle = QCheckBox(self.tr('Insert Subtitles if Available'),
                                      statusTip=sub_tip,
                                      toolTip=sub_tip)
        self.chb_subtitle.clicked.connect(self._on_modify_conversion_option)
        vertical_layout.addWidget(self.label_other_options)
        vertical_layout.addWidget(self.chb_subtitle)

        del_text = self.tr('Delete Input Video Files when Finished')
        self.chb_delete = QCheckBox(del_text,
                                    statusTip=del_text,
                                    toolTip=del_text)
        self.chb_delete.clicked.connect(self._on_modify_conversion_option)
        vertical_layout.addWidget(self.chb_delete)

        tag_text = self.tr('Use Format Tag in Output Video File Name')
        tag_tip_text = (tag_text + '. ' +
                        self.tr('Useful when Converting a '
                                'Video File to Multiples Formats'))
        self.chb_tag = QCheckBox(tag_text,
                                 statusTip=tag_tip_text,
                                 toolTip=tag_tip_text)
        self.chb_tag.clicked.connect(self._on_modify_conversion_option)
        vertical_layout.addWidget(self.chb_tag)

        shutdown_text = self.tr('Shutdown Computer when Conversion Finished')
        self.chb_shutdown = QCheckBox(shutdown_text,
                                      statusTip=shutdown_text,
                                      toolTip=shutdown_text)
        vertical_layout.addWidget(self.chb_shutdown)

        horizontal_layout.addLayout(vertical_layout)
        self.vertical_layout_1.addWidget(gb_settings)

    def _group_tasks_list(self):
        """Define the Tasks Group arrangement."""
        gb_tasks = QGroupBox(self.central_widget)
        tasks_text = self.tr('List of Conversion Tasks')
        gb_tasks.setTitle(tasks_text)
        size_policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            gb_tasks.sizePolicy().hasHeightForWidth())
        gb_tasks.setSizePolicy(size_policy)
        horizontal_layout = QHBoxLayout(gb_tasks)
        self.tb_tasks = TasksListTable(parent=gb_tasks,
                                       window=self)

        self.tb_tasks.cellPressed.connect(self._enable_context_menu_action)
        # Create a combo box for Target update
        horizontal_layout.addWidget(self.tb_tasks)
        self.vertical_layout_2.addWidget(gb_tasks)
        self.tb_tasks.doubleClicked.connect(self._update_edit_triggers)

    def _group_output_directory(self):
        """Define the output directory Group arrangement."""
        gb_output_dir = QGroupBox(self.central_widget)
        gb_output_dir.setTitle(self.tr('Output Directory'))
        vertical_layout = QVBoxLayout(gb_output_dir)
        vertical_layout_1 = QVBoxLayout()
        horizontal_layout = QHBoxLayout()
        outputdir_tip = self.tr('Choose Output Directory')
        self.le_output = QLineEdit(
            str(QDir.homePath()),
            statusTip=outputdir_tip,
            toolTip=outputdir_tip)
        self.le_output.setReadOnly(True)
        horizontal_layout.addWidget(self.le_output)
        outputbtn_tip = self.tr('Choose Output Directory')
        self.btn_output = QToolButton(
            gb_output_dir,
            statusTip=outputbtn_tip,
            toolTip=outputbtn_tip)
        self.btn_output.setIcon(QIcon(':/icons/output-folder.png'))
        self.btn_output.clicked.connect(self.output_directory)
        horizontal_layout.addWidget(self.btn_output)
        vertical_layout_1.addLayout(horizontal_layout)
        vertical_layout.addLayout(vertical_layout_1)
        self.vertical_layout_2.addWidget(gb_output_dir)

    def _group_progress(self):
        """Define the Progress Group arrangement."""
        gb_progress = QGroupBox(self.central_widget)
        gb_progress.setTitle(self.tr('Progress'))
        vertical_layout = QVBoxLayout(gb_progress)
        label_progress = QLabel(gb_progress)
        label_progress.setText(self.tr('Operation Progress'))
        vertical_layout.addWidget(label_progress)
        self.pb_progress = QProgressBar(gb_progress)
        self.pb_progress.setProperty('value', 0)
        vertical_layout.addWidget(self.pb_progress)
        label_total_progress = QLabel(gb_progress)
        label_total_progress.setText(self.tr('Total Progress'))
        vertical_layout.addWidget(label_total_progress)
        self.pb_total_progress = QProgressBar(gb_progress)
        self.pb_total_progress.setProperty('value', 0)
        vertical_layout.addWidget(self.pb_total_progress)
        self.vertical_layout_2.addWidget(gb_progress)

    def _action_factory(self, **kwargs):
        """Helper method used for creating actions.

        Args:
            text (str): Text to show in the action
            callback (method): Method to be called when action is triggered
        kwargs:
            checkable (bool): Turn the action checkable or not
            shortcut (str): Define the key shortcut to run the action
            icon (QIcon): Icon for the action
            tip (str): Tip to show in status bar or hint
        """
        action = QAction(kwargs['text'], self, triggered=kwargs['callback'])

        try:
            action.setIcon(kwargs['icon'])
        except KeyError:
            pass

        try:
            action.setShortcut(kwargs['shortcut'])
        except KeyError:
            pass

        try:
            action.setToolTip(kwargs['tip'])
            action.setStatusTip(kwargs['tip'])
        except KeyError:
            pass

        try:
            action.setCheckable(kwargs['checkable'])
        except KeyError:
            pass

        return action

    def _create_actions(self):
        """Create actions."""
        actions = {'open_media_file_action':
                   dict(icon=QIcon(':/icons/video-file.png'),
                        text=self.tr('&Add Files...'),
                        shortcut="Ctrl+O",
                        tip=self.tr('Add Video Files to the '
                                    'List of Conversion Tasks'),
                        callback=self.open_media_files),

                   'open_media_dir_action':
                   dict(icon=QIcon(':/icons/add-folder.png'),
                        text=self.tr('Add &Directory...'),
                        shortcut="Ctrl+D",
                        tip=self.tr('Add all the Video Files in a Directory '
                                    'to the List of Conversion Tasks'),
                        callback=self.open_media_dir),

                   'add_profile_action':
                   dict(icon=QIcon(':/icons/add-profile.png'),
                        text=self.tr('&Add Customized Profile...'),
                        shortcut="Ctrl+F",
                        tip=self.tr('Add Customized Profile'),
                        callback=self.add_customized_profile),

                   'export_profile_action':
                   dict(icon=QIcon(':/icons/export.png'),
                        text=self.tr('&Export Conversion Profiles...'),
                        shortcut="Ctrl+E",
                        tip=self.tr('Export Conversion Profiles'),
                        callback=self.export_profiles),

                   'import_profile_action':
                   dict(icon=QIcon(':/icons/import.png'),
                        text=self.tr('&Import Conversion Profiles...'),
                        shortcut="Ctrl+I",
                        tip=self.tr('Import Conversion Profiles'),
                        callback=self.import_profiles),

                   'restore_profile_action':
                   dict(icon=QIcon(':/icons/default-profile.png'),
                        text=self.tr('&Restore the Default '
                                     'Conversion Profiles'),
                        tip=self.tr('Restore the Default Conversion Profiles'),
                        callback=self.restore_profiles),

                   'play_input_media_file_action':
                   dict(icon=QIcon(':/icons/video-player-input.png'),
                        text=self.tr('Play Input Video File'),
                        callback=self.play_input_media_file),

                   'play_output_media_file_action':
                   dict(icon=QIcon(':/icons/video-player-output.png'),
                        text=self.tr('Play Output Video File'),
                        callback=self.play_output_media_file),

                   'clear_media_list_action':
                   dict(icon=QIcon(':/icons/clear-list.png'),
                        text=self.tr('Clear &List'),
                        shortcut="Ctrl+Del",
                        tip=self.tr('Remove all Video Files from the '
                                    'List of Conversion Tasks'),
                        callback=self.clear_media_list),

                   'remove_media_file_action':
                   dict(icon=QIcon(':/icons/remove-file.png'),
                        text=self.tr('&Remove File'),
                        shortcut="Del",
                        tip=self.tr('Remove Selected Video File from the '
                                    'List of Conversion Tasks'),
                        callback=self.remove_media_file),

                   'convert_action':
                   dict(icon=QIcon(':/icons/convert.png'),
                        text=self.tr('&Convert'),
                        shortcut="Ctrl+R",
                        tip=self.tr('Start Conversion Process'),
                        callback=self.start_encoding),

                   'stop_action':
                   dict(icon=QIcon(':/icons/stop.png'),
                        text=self.tr('&Stop'),
                        shortcut="Ctrl+P",
                        tip=self.tr('Stop Video File Conversion'),
                        callback=self.stop_file_encoding),

                   'stop_all_action':
                   dict(icon=QIcon(':/icons/stop-all.png'),
                        text=self.tr('S&top All'),
                        shortcut="Ctrl+A",
                        tip=self.tr('Stop all Video Conversion Tasks'),
                        callback=self.stop_all_files_encoding),

                   'about_action':
                   dict(text=self.tr('&About') + ' ' + APP_NAME,
                        tip=self.tr('About') + ' ' + APP_NAME + ' ' + VERSION,
                        callback=self.controller.on_about_action_clicked),

                   'help_content_action':
                   dict(icon=QIcon(':/icons/about.png'),
                        text=self.tr('&Contents'),
                        shortcut="Ctrl+H",
                        tip=self.tr('Help Contents'),
                        callback=self.help_content),

                   'changelog_action':
                   dict(icon=QIcon(':/icons/changelog.png'),
                        text=self.tr('Changelog'),
                        tip=self.tr('Changelog'),
                        callback=self.controller.on_changelog_action_clicked),

                   'ffmpeg_doc_action':
                   dict(icon=QIcon(':/icons/ffmpeg.png'),
                        text=self.tr('&Ffmpeg Documentation'),
                        shortcut="Ctrl+L",
                        tip=self.tr('Open Ffmpeg On-Line Documentation'),
                        callback=self.ffmpeg_doc),

                   'videomorph_web_action':
                   dict(icon=QIcon(':/logo/videomorph.png'),
                        text=APP_NAME + ' ' + self.tr('&Web Page'),
                        shortcut="Ctrl+V",
                        tip=self.tr('Open') + ' ' + APP_NAME + ' ' + self.tr(
                            'Web Page'),
                        callback=self.videomorph_web),

                   'exit_action':
                   dict(icon=QIcon(':/icons/exit.png'),
                        text=self.tr('E&xit'),
                        shortcut="Ctrl+Q",
                        tip=self.tr('Exit') + ' ' + APP_NAME + ' ' + VERSION,
                        callback=self.close),

                   'info_action':
                   dict(text=self.tr('Properties...'),
                        tip=self.tr('Show Video Properties'),
                        callback=self.show_video_info)}

        for action in actions:
            self.__dict__[action] = self._action_factory(**actions[action])

    def _create_context_menu(self):
        first_separator = QAction(self)
        first_separator.setSeparator(True)
        second_separator = QAction(self)
        second_separator.setSeparator(True)
        self.tb_tasks.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.tb_tasks.addAction(self.open_media_file_action)
        self.tb_tasks.addAction(self.open_media_dir_action)
        self.tb_tasks.addAction(first_separator)
        self.tb_tasks.addAction(self.remove_media_file_action)
        self.tb_tasks.addAction(self.clear_media_list_action)
        self.tb_tasks.addAction(second_separator)
        self.tb_tasks.addAction(self.play_input_media_file_action)
        self.tb_tasks.addAction(self.play_output_media_file_action)
        self.tb_tasks.addAction(self.info_action)

    def _create_main_menu(self):
        """Create main app menu."""
        # File menu
        self.file_menu = self.menuBar().addMenu(self.tr('&File'))
        self.file_menu.addAction(self.open_media_file_action)
        self.file_menu.addAction(self.open_media_dir_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)
        # Edit menu
        self.edit_menu = self.menuBar().addMenu(self.tr('&Edit'))
        self.edit_menu.addAction(self.add_profile_action)
        self.edit_menu.addAction(self.export_profile_action)
        self.edit_menu.addAction(self.import_profile_action)
        self.edit_menu.addAction(self.restore_profile_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.clear_media_list_action)
        self.edit_menu.addAction(self.remove_media_file_action)
        # Conversion menu
        self.conversion_menu = self.menuBar().addMenu(self.tr('&Conversion'))
        self.conversion_menu.addAction(self.convert_action)
        self.conversion_menu.addAction(self.stop_action)
        self.conversion_menu.addSeparator()
        self.conversion_menu.addAction(self.stop_all_action)
        # Help menu
        self.help_menu = self.menuBar().addMenu(self.tr('&Help'))
        self.help_menu.addAction(self.help_content_action)
        self.help_menu.addAction(self.changelog_action)
        self.help_menu.addAction(self.videomorph_web_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.ffmpeg_doc_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_action)

    def _create_toolbar(self):
        """Create a toolbar and add it to the interface."""
        self.tool_bar = QToolBar(self)
        # Add actions to the tool bar
        self.tool_bar.addAction(self.open_media_file_action)
        self.tool_bar.addSeparator()
        self.tool_bar.addAction(self.clear_media_list_action)
        self.tool_bar.addAction(self.remove_media_file_action)
        self.tool_bar.addSeparator()
        self.tool_bar.addAction(self.convert_action)
        self.tool_bar.addAction(self.stop_action)
        self.tool_bar.addAction(self.stop_all_action)
        self.tool_bar.addSeparator()
        self.tool_bar.addAction(self.exit_action)
        self.tool_bar.setIconSize(QSize(28, 28))
        # Add the toolbar to main window
        self.addToolBar(Qt.TopToolBarArea, self.tool_bar)

    def _create_status_bar(self):
        """Create app status bar."""
        self.statusBar().showMessage(self.tr('Ready'))

    def _create_progress_dialog(self):
        label = QLabel()
        label.setAlignment(Qt.AlignLeft)
        progress_dlg = QProgressDialog(parent=self)
        progress_dlg.setFixedSize(500, 100)
        progress_dlg.setWindowTitle(self.tr('Adding Video Files...'))
        progress_dlg.setCancelButtonText(self.tr('Cancel'))
        progress_dlg.setLabel(label)
        progress_dlg.setModal(True)
        progress_dlg.setMinimum(0)
        progress_dlg.setMinimumDuration(0)
        progress_dlg.setMaximum(0)
        progress_dlg.setValue(0)

        return progress_dlg

    def _fix_layout(self):
        """Fix widgets layout."""
        spacer_item = QSpacerItem(20,
                                  40,
                                  QSizePolicy.Minimum,
                                  QSizePolicy.Expanding)
        self.vertical_layout_1.addItem(spacer_item)
        self.horizontal_layout.addLayout(self.vertical_layout_1)

    def _update_edit_triggers(self):
        """Toggle Edit triggers on task table."""
        if (int(self.tb_tasks.currentColumn()) == COLUMNS.QUALITY and not
                self.conversion_lib.converter_is_running):
            self.tb_tasks.setEditTriggers(QAbstractItemView.AllEditTriggers)
        else:
            self.tb_tasks.setEditTriggers(QAbstractItemView.NoEditTriggers)
            if int(self.tb_tasks.currentColumn()) == COLUMNS.NAME:
                self.play_input_media_file()

        self._update_ui_when_playing(row=self.tb_tasks.currentIndex().row())

    @staticmethod
    def _get_settings_file():
        return QSettings(join_path(SYS_PATHS.config, 'config.ini'),
                         QSettings.IniFormat)

    def _create_initial_settings(self):
        """Create initial settings file."""
        if not exists(join_path(SYS_PATHS.config, 'config.ini')):
            self._write_app_settings(pos=QPoint(100, 50),
                                     size=QSize(1096, 510),
                                     profile_index=0,
                                     preset_index=0)

    def _read_app_settings(self):
        """Read the app settings."""
        settings = self._get_settings_file()
        pos = settings.value("pos", QPoint(600, 200), type=QPoint)
        size = settings.value("size", QSize(1096, 510), type=QSize)
        self.resize(size)
        self.move(pos)
        if 'profile_index' and 'preset_index' in settings.allKeys():
            profile = settings.value('profile_index')
            preset = settings.value('preset_index')
            self.cb_profiles.setCurrentIndex(int(profile))
            self.cb_quality.setCurrentIndex(int(preset))
        if 'output_dir' in settings.allKeys():
            directory = str(settings.value('output_dir'))
            output_dir = directory if isdir(directory) else QDir.homePath()
            self.le_output.setText(output_dir)
        if 'source_dir' in settings.allKeys():
            self.source_dir = str(settings.value('source_dir'))

    def _write_app_settings(self, **app_settings):
        """Write app settings on exit.

        Args:
            app_settings (OrderedDict): OrderedDict to collect all app settings
        """
        settings_file = self._get_settings_file()

        settings = OrderedDict(
            pos=self.pos(),
            size=self.size(),
            profile_index=self.cb_profiles.currentIndex(),
            preset_index=self.cb_quality.currentIndex(),
            source_dir=self.source_dir,
            output_dir=self.le_output.text())

        if app_settings:
            settings.update(app_settings)

        for key, setting in settings.items():
            settings_file.setValue(key, setting)

    def _show_message_box(self, type_, title, msg):
        QMessageBox(type_, title, msg, QMessageBox.Ok, self).show()

    def ffmpeg_doc(self):
        """Open ffmpeg documentation page."""
        self._open_url(url='https://ffmpeg.org/documentation.html')

    def videomorph_web(self):
        """Open VideoMorph Web page."""
        self._open_url(url='http://videomorph.webmisolutions.com')

    def show_video_info(self):
        """Show video info on the Info Panel."""
        position = self.tb_tasks.currentRow()
        info_dlg = InfoDialog(parent=self,
                              position=position,
                              media_list=self.media_list)
        info_dlg.show()

    def notify(self, file_name):
        """Notify when conversion finished."""
        file_name = ''.join(('"', file_name, '"'))
        msg = file_name + ': ' + self.tr('Successfully converted')
        self.tray_icon.showMessage(APP_NAME, msg,
                                   QSystemTrayIcon.Information, 2000)
        if exists(join_path(BASE_DIR, VM_PATHS.sounds)):
            sound = join_path(BASE_DIR, VM_PATHS.sounds, 'successful.wav')
        else:
            sound = join_path(SYS_PATHS.sounds, 'successful.wav')
        launcher = launcher_factory()
        launcher.sound_notify(sound)

    @staticmethod
    def _open_url(url):
        """Open URL."""
        launcher = launcher_factory()
        launcher.open_with_user_browser(url=url)

    @staticmethod
    def help_content():
        """Open ffmpeg documentation page."""
        if LOCALE == 'es_ES':
            file_name = 'manual_es.pdf'
        else:
            file_name = 'manual_en.pdf'

        file_path = join_path(SYS_PATHS.help, file_name)
        if isfile(file_path):
            url = join_path('file:', file_path)
        else:
            url = join_path('file:', BASE_DIR, VM_PATHS.help, file_name)

        launcher = launcher_factory()
        launcher.open_with_user_browser(url=url)

    @staticmethod
    def shutdown_machine():
        """Shutdown machine when conversion is finished."""
        launcher = launcher_factory()
        qApp.closeAllWindows()
        launcher.shutdown_machine()

    def populate_profiles_combo(self):
        """Populate profiles combobox."""
        # Clear combobox content
        self.cb_profiles.clear()
        # Populate the combobox with new data

        profile_names = self.profile.get_xml_profile_qualities(LOCALE).keys()
        for i, profile_name in enumerate(profile_names):
            self.cb_profiles.addItem(profile_name)
            icon = QIcon(':/formats/{0}.png'.format(profile_name))
            self.cb_profiles.setItemIcon(i, icon)

    def populate_quality_combo(self, combo):
        """Populate target quality combobox.

        Args:
            combo (QComboBox): List all available presets
        """
        current_profile = self.cb_profiles.currentText()
        if current_profile != '':
            combo.clear()
            combo.addItems(
                self.profile.get_xml_profile_qualities(
                    LOCALE)[current_profile])

            if self.tb_tasks.rowCount():
                self._update_media_files_status()
            self.profile.update(new_quality=self.cb_quality.currentText())

    def output_directory(self):
        """Choose output directory."""
        directory = self._select_directory(
            dialog_title=self.tr('Choose Output Directory'),
            source_dir=self.le_output.text())

        if directory:
            self.le_output.setText(directory)
            self._on_modify_conversion_option()

    def closeEvent(self, event):
        """Things to do on close."""
        # Close communication and kill the encoding process
        if self.conversion_lib.converter_is_running:
            # ask for confirmation
            user_answer = QMessageBox.question(
                self,
                APP_NAME,
                self.tr('There are on Going Conversion Tasks.'
                        ' Are you Sure you Want to Exit?'),
                QMessageBox.Yes | QMessageBox.No)

            if user_answer == QMessageBox.Yes:
                # Disconnect the finished signal
                self.conversion_lib.converter_finished_disconnect(
                    connected=self._finish_file_encoding)
                self.conversion_lib.kill_converter()
                self.conversion_lib.close_converter()
                self.media_list.delete_running_file_output(
                    output_dir=self.le_output.text(),
                    tagged_output=self.chb_tag.checkState())
                # Save settings
                self._write_app_settings()
                event.accept()
            else:
                event.ignore()
        else:
            # Save settings
            self._write_app_settings()
            event.accept()

    def _fill_media_list(self, files_paths):
        """Fill MediaList object with _MediaFile objects."""
        progress_dlg = self._create_progress_dialog()

        for i, element in enumerate(self.media_list.populate(files_paths)):
            if not i:  # First element yielded
                progress_dlg.setMaximum(element)
            else:  # Second and on...
                progress_dlg.setLabelText(self.tr('Adding File: ') + element)
                progress_dlg.setValue(i)

            if progress_dlg.wasCanceled():
                break

        progress_dlg.close()

        if self.media_list.not_added_files:
            msg = self.tr('Invalid Video File Information for:') + ' \n - ' + \
                  '\n - '.join(self.media_list.not_added_files) + '\n' + \
                  self.tr('File not Added to the List of Conversion Tasks')
            self._show_message_box(
                type_=QMessageBox.Critical,
                title=self.tr('Error!'),
                msg=msg)

            if not self.media_list.length:
                self._update_ui_when_no_file()
            else:
                self.update_ui_when_ready()

    def _load_files(self, source_dir=QDir.homePath()):
        """Load video files."""
        files_paths = self._select_files(
            dialog_title=self.tr('Select Video Files'),
            files_filter=self.tr('Video Files') + ' ' +
            '(' + VIDEO_FILTERS + ')',
            source_dir=source_dir)

        return files_paths

    def _insert_table_item(self, item_text, row, column):
        item = QTableWidgetItem()
        item.setText(item_text)
        if column == COLUMNS.NAME:
            item.setIcon(QIcon(':/icons/video-in-list.png'))
        self.tb_tasks.setItem(row, column, item)

    def _create_table(self):
        self.tb_tasks.setRowCount(self.media_list.length)
        # Call converter_is_running only once
        converter_is_running = self.conversion_lib.converter_is_running
        for row in range(self.tb_tasks.rowCount()):
            self._insert_table_item(
                item_text=self.media_list.get_file_name(position=row,
                                                        with_extension=True),
                row=row, column=COLUMNS.NAME)

            self._insert_table_item(
                item_text=str(write_time(
                    self.media_list.get_file_info(
                        position=row,
                        info_param='duration'))),
                row=row, column=COLUMNS.DURATION)

            self._insert_table_item(
                item_text=str(self.cb_quality.currentText()),
                row=row, column=COLUMNS.QUALITY)

            if converter_is_running:
                if row > self.media_list.position:
                    self._insert_table_item(item_text=self.tr('To Convert'),
                                            row=row, column=COLUMNS.PROGRESS)
            else:
                self._insert_table_item(item_text=self.tr('To Convert'),
                                        row=row, column=COLUMNS.PROGRESS)

    def add_media_files(self, *files):
        """Add video files to conversion list.

        Args:
            files (list): List of video file paths
        """
        # Update tool buttons so you can convert, or add_file, or clear...
        # only if there is not a conversion process running
        if self.conversion_lib.converter_is_running:
            self._update_ui_when_converter_running()
        else:
            # Update the files status
            self._set_media_status()
            # Update ui
            self.update_ui_when_ready()

        self._fill_media_list(files)

        self._create_table()

        # After adding files to the list, recalculate the list duration
        self.media_list_duration = self.media_list.duration

    def play_input_media_file(self):
        """Play the input video using an available video player."""
        row = self.tb_tasks.currentIndex().row()
        self._play_media_file(file_path=self.media_list.get_file_path(row))
        self._update_ui_when_playing(row)

    def _get_output_path(self, row):
        path = self.media_list.get_file(row).get_output_path(
            output_dir=self.le_output.text(),
            tagged_output=self.chb_tag.checkState())
        return path

    def play_output_media_file(self):
        """Play the output video using an available video player."""
        row = self.tb_tasks.currentIndex().row()
        path = self._get_output_path(row)
        self._play_media_file(file_path=path)
        self._update_ui_when_playing(row)

    def _play_media_file(self, file_path):
        """Play a video using an available video player."""
        try:
            self.conversion_lib.run_player(file_path=file_path)
        except PlayerNotFoundError:
            self._show_message_box(
                type_=QMessageBox.Critical,
                title=self.tr('Error!'),
                msg=self.tr('No Video Player Found in your System'))

    def open_media_files(self):
        """Add media files to the list of conversion tasks."""
        files_paths = self._load_files(source_dir=self.source_dir)
        # If no file is selected then return
        if files_paths is None:
            return

        self.add_media_files(*files_paths)

    def open_media_dir(self):
        """Add media files from a directory recursively."""
        directory = self._select_directory(
            dialog_title=self.tr('Select Directory'),
            source_dir=self.source_dir)

        if not directory:
            return

        try:
            media_files = search_directory_recursively(directory)
            self.source_dir = directory
            self.add_media_files(*media_files)
        except FileNotFoundError:
            self._show_message_box(
                type_=QMessageBox.Critical,
                title=self.tr('Error!'),
                msg=self.tr('No Video Files Found in:' + ' ' + directory))

    def remove_media_file(self):
        """Remove selected media file from the list."""
        file_row = self.tb_tasks.currentItem().row()

        msg_box = QMessageBox(
            QMessageBox.Warning,
            self.tr('Warning!'),
            self.tr('Remove Video File from the List of Conversion Tasks?'),
            QMessageBox.NoButton, self)

        msg_box.addButton(self.tr("&Yes"), QMessageBox.AcceptRole)
        msg_box.addButton(self.tr("&No"), QMessageBox.RejectRole)

        if msg_box.exec_() == QMessageBox.AcceptRole:
            # Delete file from table
            self.tb_tasks.removeRow(file_row)
            # Remove file from self.media_list
            self.media_list.delete_file(position=file_row)
            self.media_list.position = None
            self.media_list_duration = self.media_list.duration

        # If all files are deleted... update the interface
        if not self.tb_tasks.rowCount():
            self._reset_options_check_boxes()
            self._update_ui_when_no_file()

    def add_customized_profile(self):
        """Show dialog for adding conversion profiles."""
        add_profile_dlg = AddProfileDialog(parent=self)
        add_profile_dlg.exec_()

    def _export_import_profiles(self, func, path, msg_info):
        try:
            func(path)
        except PermissionError:
            self._show_message_box(
                type_=QMessageBox.Critical,
                title=self.tr('Error!'),
                msg=self.tr('Can not Write to Selected Directory'))
        else:
            self._show_message_box(type_=QMessageBox.Information,
                                   title=self.tr('Information!'),
                                   msg=msg_info)

    def _select_directory(self, dialog_title, source_dir=QDir.homePath()):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly

        directory = QFileDialog.getExistingDirectory(self,
                                                     dialog_title,
                                                     source_dir,
                                                     options=options)
        return directory

    def export_profiles(self):
        """Export conversion profiles."""
        directory = self._select_directory(
            dialog_title=self.tr('Export to Directory'))

        if directory:
            msg_info = self.tr('Conversion Profiles Successfully Exported!')
            self._export_import_profiles(
                func=self.profile.export_xml_profiles,
                path=directory, msg_info=msg_info)

    def import_profiles(self):
        """Import conversion profiles."""
        file_path = self._select_files(
            dialog_title=self.tr('Select a Profiles File'),
            files_filter=self.tr('Profiles Files ') + '(*.xml)',
            single_file=True)

        if file_path:
            msg_info = self.tr('Conversion Profiles Successfully Imported!')

            self._export_import_profiles(
                func=self.profile.import_xml_profiles,
                path=file_path, msg_info=msg_info)
            self.populate_profiles_combo()
            self.profile.update(new_quality=self.cb_quality.currentText())

    def restore_profiles(self):
        """Restore default profiles."""
        msg_box = QMessageBox(
            QMessageBox.Warning,
            self.tr('Warning!'),
            self.tr('Do you Really Want to Restore the '
                    'Default Conversion Profiles?'),
            QMessageBox.NoButton, self)

        msg_box.addButton(self.tr("&Yes"), QMessageBox.AcceptRole)
        msg_box.addButton(self.tr("&No"), QMessageBox.RejectRole)

        if msg_box.exec_() == QMessageBox.AcceptRole:
            self.profile.restore_default_profiles()
            self.populate_profiles_combo()
            self.profile.update(new_quality=self.cb_quality.currentText())

    def _select_files(self, dialog_title, files_filter,
                      source_dir=QDir.homePath(), single_file=False):
        # Validate source_dir
        source_directory = source_dir if isdir(source_dir) else QDir.homePath()

        # Select media files and store their path
        if single_file:
            files_paths, _ = QFileDialog.getOpenFileName(self,
                                                         dialog_title,
                                                         source_directory,
                                                         files_filter)
        else:
            files_paths, _ = QFileDialog.getOpenFileNames(self,
                                                          dialog_title,
                                                          source_directory,
                                                          files_filter)

        if files_paths:
            # Update the source directory
            if not single_file:
                self.source_dir = dirname(files_paths[0])
        else:
            return None

        return files_paths

    def clear_media_list(self):
        """Clear media conversion list with user confirmation."""
        msg_box = QMessageBox(
            QMessageBox.Warning,
            self.tr('Warning!'),
            self.tr('Remove all Conversion Tasks from the List?'),
            QMessageBox.NoButton, self)

        msg_box.addButton(self.tr("&Yes"), QMessageBox.AcceptRole)
        msg_box.addButton(self.tr("&No"), QMessageBox.RejectRole)

        if msg_box.exec_() == QMessageBox.AcceptRole:
            # If user says YES clear table of conversion tasks
            self.tb_tasks.clearContents()
            self.tb_tasks.setRowCount(0)
            # Clear MediaList so it contains no element
            self.media_list.clear()
            # Update UI
            self._reset_options_check_boxes()
            self._update_ui_when_no_file()

    def start_encoding(self):
        """Start the encoding process."""
        self._update_ui_when_converter_running()

        self.media_list.position += 1
        self.timer.operation_start_time = 0.0

        if self.media_list.running_file_status == STATUS.todo:
            try:
                # Fist build the conversion command
                conversion_cmd = self.media_list.running_file_conversion_cmd(
                    target_quality=self.tb_tasks.item(
                        self.media_list.position,
                        COLUMNS.QUALITY).text(),
                    output_dir=self.le_output.text(),
                    tagged_output=self.chb_tag.checkState(),
                    subtitle=bool(self.chb_subtitle.checkState()))
                # Then pass it to the _converter
                self.conversion_lib.start_converter(cmd=conversion_cmd)
            except PermissionError:
                self._show_message_box(
                    type_=QMessageBox.Critical,
                    title=self.tr('Error!'),
                    msg=self.tr('Can not Write to Selected Directory'))
                self._update_ui_when_error_on_conversion()
            except FileNotFoundError:
                self._show_message_box(
                    type_=QMessageBox.Critical,
                    title=self.tr('Error!'),
                    msg=(self.tr('Input Video File:') + ' ' +
                         self.media_list.running_file_name(
                             with_extension=True) + ' ' +
                         self.tr('not Found')))
                self._update_ui_when_error_on_conversion()
            except FileExistsError:
                self._show_message_box(
                    type_=QMessageBox.Critical,
                    title=self.tr('Error!'),
                    msg=(self.tr('Video File:') + ' ' +
                         self.media_list.running_file_output_name(
                             output_dir=self.le_output.text(),
                             tagged_output=self.chb_tag.checkState()) + ' ' +
                         self.tr('Already Exists in '
                                 'Output Directory. Please, Change the '
                                 'Output Directory')))
                self._update_ui_when_error_on_conversion()
        else:
            self._end_encoding_process()

    def stop_file_encoding(self):
        """Stop file encoding process and continue with the list."""
        # Terminate the file encoding
        self.conversion_lib.stop_converter()
        # Set _MediaFile.status attribute
        self.media_list.running_file_status = STATUS.stopped
        # Delete the file when conversion is stopped by the user
        self.media_list.delete_running_file_output(
            output_dir=self.le_output.text(),
            tagged_output=self.chb_tag.checkState())
        # Update the list duration and partial time for total progress bar
        self.timer.reset_progress_times()
        self.media_list_duration = self.media_list.duration

    def stop_all_files_encoding(self):
        """Stop the conversion process for all the files in list."""
        # Delete the file when conversion is stopped by the user
        self.conversion_lib.stop_converter()
        self.media_list.delete_running_file_output(
            output_dir=self.le_output.text(),
            tagged_output=self.chb_tag.checkState())
        for media_file in self.media_list:
            # Set _MediaFile.status attribute
            if media_file.status != STATUS.done:
                media_file.status = STATUS.stopped
                self.media_list.position = self.media_list.index(media_file)
                self.tb_tasks.item(
                    self.media_list.position,
                    COLUMNS.PROGRESS).setText(self.tr('Stopped!'))

        # Update the list duration and partial time for total progress bar
        self.timer.reset_progress_times()
        self.media_list_duration = self.media_list.duration

    def _finish_file_encoding(self):
        """Finish the file encoding process."""
        if self.media_list.running_file_status != STATUS.stopped:
            file_name = self.media_list.running_file_name(with_extension=True)
            self.notify(file_name)
            # Close and kill the converterprocess
            self.conversion_lib.close_converter()
            # Check if the process finished OK
            if (self.conversion_lib.converter_exit_status() ==
                    QProcess.NormalExit):
                # When finished a file conversion...
                self.tb_tasks.item(self.media_list.position,
                                   COLUMNS.PROGRESS).setText(self.tr('Done!'))
                self.media_list.running_file_status = STATUS.done
                self.pb_progress.setProperty("value", 0)
                if self.chb_delete.checkState():
                    self.media_list.delete_running_file_input()
        else:
            # If the process was stopped
            if not self.conversion_lib.converter_is_running:
                self.tb_tasks.item(
                    self.media_list.position,
                    COLUMNS.PROGRESS).setText(self.tr('Stopped!'))
        # Attempt to end the conversion process
        self._end_encoding_process()

    def _end_encoding_process(self):
        """End up the encoding process."""
        # Test if encoding process is finished
        if self.media_list.is_exhausted:

            if self.conversion_lib.error is not None:
                self._show_message_box(
                    type_=QMessageBox.Critical,
                    title='Error!',
                    msg=self.tr('The Conversion Library has '
                                'Failed with Error:') + ' ' +
                    self.conversion_lib.error)
                self.conversion_lib.error = None
            elif not self.media_list.all_stopped:
                if self.chb_shutdown.checkState():
                    self.shutdown_machine()
                    return
                self._show_message_box(
                    type_=QMessageBox.Information,
                    title=self.tr('Information!'),
                    msg=self.tr('Encoding Process Successfully Finished!'))
            else:
                self._show_message_box(
                    type_=QMessageBox.Information,
                    title=self.tr('Information!'),
                    msg=self.tr('Encoding Process Stopped by the User!'))

            self._set_window_title()
            self.statusBar().showMessage(self.tr('Ready'))
            self._reset_options_check_boxes()
            # Reset all progress related variables
            self._reset_progress_bars()
            self.timer.reset_progress_times()
            self.media_list_duration = self.media_list.duration
            self.timer.process_start_time = 0.0
            # Reset the position
            self.media_list.position = None
            # Update tool buttons
            self._update_ui_when_problem()
        else:
            self.start_encoding()

    def _set_window_title(self):
        """Set window title."""
        self.setWindowTitle(APP_NAME + ' ' + VERSION)

    def _reset_progress_bars(self):
        """Reset the progress bars."""
        self.pb_progress.setProperty("value", 0)
        self.pb_total_progress.setProperty("value", 0)

    def _ready_read(self):
        """Is called when the conversion process emit a new output."""
        self.reader.update_read(
            process_output=self.conversion_lib.read_converter_output())

        self._update_conversion_progress()

    def _update_conversion_progress(self):
        """Read the encoding output from the converter stdout."""
        # Initialize the process time
        if not self.timer.process_start_time:
            self.timer.init_process_start_time()

        # Initialize the operation time
        if not self.timer.operation_start_time:
            self.timer.init_operation_start_time()

        # Return if no time read
        if not self.reader.has_time_read:
            # Catch the library errors only before time_read
            self.conversion_lib.catch_errors()
            return

        self.timer.update_time(op_time_read_sec=self.reader.time)

        self.timer.update_cum_times()

        file_duration = float(self.media_list.running_file_info('duration'))

        operation_progress = self.timer.operation_progress(
            file_duration=file_duration)

        process_progress = self.timer.process_progress(
            list_duration=self.media_list_duration)

        self._update_progress(op_progress=operation_progress,
                              pr_progress=process_progress)

        self._update_status_bar()

        self._update_main_window_title(op_progress=operation_progress)

    def _update_progress(self, op_progress, pr_progress):
        """Update operation progress in tasks list & operation progress bar."""
        # Update operation progress bar
        self.pb_progress.setProperty("value", op_progress)
        # Update operation progress in tasks list
        self.tb_tasks.item(self.media_list.position, 3).setText(
            str(op_progress) + "%")
        self.pb_total_progress.setProperty("value", pr_progress)

    def _update_main_window_title(self, op_progress):
        """Update the main window title."""
        running_file_name = self.media_list.running_file_name(
            with_extension=True)

        self.setWindowTitle(str(op_progress) + '%' + '-' +
                            '[' + running_file_name + ']' +
                            ' - ' + APP_NAME + ' ' + VERSION)

    def _update_status_bar(self):
        """Update the status bar while converting."""
        file_duration = float(self.media_list.running_file_info('duration'))

        self.statusBar().showMessage(
            self.tr('Converting: {m}\t\t\t '
                    'At: {br}\t\t\t '
                    'Operation Remaining Time: {ort}\t\t\t '
                    'Total Elapsed Time: {tet}').format(
                        m=self.media_list.running_file_name(
                            with_extension=True),
                        br=self.reader.bitrate,
                        ort=self.timer.operation_remaining_time(
                            file_duration=file_duration),
                        tet=write_time(self.timer.process_cum_time)))

    def _update_media_files_status(self):
        """Update file status."""
        # Current item
        item = self.tb_tasks.currentItem()
        if item is not None:
            # Update target_quality in table
            self.tb_tasks.item(item.row(), COLUMNS.QUALITY).setText(
                str(self.cb_quality.currentText()))

            # Update table Progress field if file is: Done or Stopped
            self.update_table_progress_column(row=item.row())

            # Update file Done or Stopped status
            self.media_list.set_file_status(position=item.row(),
                                            status=STATUS.todo)

        else:
            self._update_all_table_rows(column=COLUMNS.QUALITY,
                                        value=self.cb_quality.currentText())

            self._set_media_status()

        # Update total duration of the new tasks list
        self.media_list_duration = self.media_list.duration
        # Update the interface
        self.update_ui_when_ready()

    def _update_all_table_rows(self, column, value):
        rows = self.tb_tasks.rowCount()
        if rows:
            for row in range(rows):
                self.tb_tasks.item(row, column).setText(
                    str(value))
                self.update_table_progress_column(row)

    def update_table_progress_column(self, row):
        """Update the progress column of conversion task list."""
        if self.media_list.get_file_status(row) != STATUS.todo:
            self.tb_tasks.item(
                row,
                COLUMNS.PROGRESS).setText(self.tr('To Convert'))

    def _reset_options_check_boxes(self):
        self.chb_delete.setChecked(False)
        self.chb_tag.setChecked(False)
        self.chb_subtitle.setChecked(False)
        self.chb_shutdown.setChecked(False)

    def _set_media_status(self):
        """Update media files state of conversion."""
        for media_file in self.media_list:
            media_file.status = STATUS.todo
        self.media_list.position = None

    def _on_modify_conversion_option(self):
        if self.media_list.length:
            self.update_ui_when_ready()
            self._set_media_status()
            self._update_all_table_rows(column=COLUMNS.PROGRESS,
                                        value=self.tr('To Convert'))
            self.media_list_duration = self.media_list.duration

    def _update_ui(self, **i_vars):
        """Update the interface status.

        Args:
            i_vars (dict): Dict to collect all the interface variables
        """
        variables = dict(add=True,
                         convert=True,
                         clear=True,
                         remove=True,
                         stop=True,
                         stop_all=True,
                         presets=True,
                         profiles=True,
                         add_costume_profile=True,
                         import_profile=True,
                         restore_profile=True,
                         output_dir=True,
                         subtitles_chb=True,
                         delete_chb=True,
                         tag_chb=True,
                         shutdown_chb=True,
                         play_input=True,
                         play_output=True,
                         info=True)

        variables.update(i_vars)

        self.open_media_file_action.setEnabled(variables['add'])
        self.convert_action.setEnabled(variables['convert'])
        self.clear_media_list_action.setEnabled(variables['clear'])
        self.remove_media_file_action.setEnabled(variables['remove'])
        self.stop_action.setEnabled(variables['stop'])
        self.stop_all_action.setEnabled(variables['stop_all'])
        self.cb_quality.setEnabled(variables['presets'])
        self.cb_profiles.setEnabled(variables['profiles'])
        self.add_profile_action.setEnabled(variables['add_costume_profile'])
        self.import_profile_action.setEnabled(variables['import_profile'])
        self.restore_profile_action.setEnabled(variables['restore_profile'])
        self.btn_output.setEnabled(variables['output_dir'])
        self.chb_subtitle.setEnabled(variables['subtitles_chb'])
        self.chb_delete.setEnabled(variables['delete_chb'])
        self.chb_tag.setEnabled(variables['tag_chb'])
        self.chb_shutdown.setEnabled(variables['shutdown_chb'])
        self.play_input_media_file_action.setEnabled(variables['play_input'])
        self.play_output_media_file_action.setEnabled(variables['play_output'])
        self.info_action.setEnabled(variables['info'])
        self.tb_tasks.setCurrentItem(None)

    def _update_ui_when_no_file(self):
        """User cannot perform any action but to add files to list."""
        self._update_ui(clear=False,
                        remove=False,
                        convert=False,
                        stop=False,
                        stop_all=False,
                        profiles=False,
                        presets=False,
                        subtitles_chb=False,
                        delete_chb=False,
                        tag_chb=False,
                        shutdown_chb=False,
                        play_input=False,
                        play_output=False,
                        info=False)

    def update_ui_when_ready(self):
        """Update UI when app is ready to start conversion."""
        self._update_ui(stop=False,
                        stop_all=False,
                        remove=False,
                        play_input=False,
                        play_output=False,
                        info=False)

    def _update_ui_when_playing(self, row):
        if self.conversion_lib.converter_is_running:
            self._update_ui_when_converter_running()
        elif self.media_list.get_file_status(row) == STATUS.todo:
            self.update_ui_when_ready()
        else:
            self._update_ui_when_problem()

    def _update_ui_when_problem(self):
        self._update_ui(convert=False,
                        stop=False,
                        stop_all=False,
                        remove=False,
                        play_input=False,
                        play_output=False,
                        info=False)

    def _update_ui_when_converter_running(self):
        self._update_ui(presets=False,
                        profiles=False,
                        subtitles_chb=False,
                        add_costume_profile=False,
                        import_profile=False,
                        restore_profile=False,
                        convert=False,
                        clear=False,
                        remove=False,
                        output_dir=False,
                        delete_chb=False,
                        tag_chb=False,
                        play_input=False,
                        play_output=False,
                        info=False)

    def _update_ui_when_error_on_conversion(self):
        self.timer.reset_progress_times()
        self.media_list_duration = self.media_list.duration
        self.media_list.position = None
        self._reset_progress_bars()
        self._set_window_title()
        self._reset_options_check_boxes()
        self.update_ui_when_ready()

    def _enable_context_menu_action(self):
        if not self.conversion_lib.converter_is_running:
            self.remove_media_file_action.setEnabled(True)

        self.play_input_media_file_action.setEnabled(True)

        path = self._get_output_path(row=self.tb_tasks.currentIndex().row())
        # Only enable the menu if output file exist and if it not .mp4,
        # cause .mp4 files doesn't run until conversion is finished
        self.play_output_media_file_action.setEnabled(
            exists(path) and self.cb_profiles.currentText() != 'MP4')
        self.info_action.setEnabled(bool(self.media_list.length))
