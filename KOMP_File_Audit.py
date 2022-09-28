# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 10:09:16 2022

@author: wardc
"""

__VERSION__ = '1.0.0'

#%% import libraries

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtCore import QAbstractTableModel, QModelIndex 
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel, QPushButton 
from PyQt5.QtWidgets import QTextEdit, QTableView, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QFileDialog, QComboBox
import pandas
import sys
import re
import os

#%% define functions
def html_text_color(text,color):
    text_output = f'<span style="color:{color}">{text}</span><br>'

    return text_output



def filename_audit(mouse_list,file_list,file_suffixes,basename_length,assignment=None):
    barcode_finder = re.compile(
        '^(?P<prefix>M?0*)(?P<barcode>.+?)(-wt)?(\s)?(?P<assignment>\(.*?\))?(?P<suffix>[\.|-].*)?$'
        )
    
    anticipated_files = []
    # generate expected filename list
    for a in list(mouse_list['parsed_mouse_list']):
        parsed_mouse = re.search(barcode_finder,a)
        if assignment is not None and not any(
                [i in parsed_mouse['assignment'] for i in assignment]
                ):
            continue
        
        if parsed_mouse['prefix'] == '':
            prefix = 'M'+'0'*(basename_length-len(parsed_mouse['barcode']))
        else:
            prefix = parsed_mouse['prefix']
        for s in file_suffixes:
            anticipated_files.append(prefix+parsed_mouse['barcode']+s)
            
    anticipated_set = set(anticipated_files)
    
    actual_set = set(list(file_list['filename']))
    
    # compare expected vs actual for match vs mismatch
    missing_files = anticipated_set.difference(actual_set)
    passing_files = anticipated_set.intersection(actual_set)
    unexpected_files = actual_set.difference(anticipated_set)
    
    missing_mice = {re.search(barcode_finder,a)['barcode'] for a in missing_files}
    passing_mice = {re.search(barcode_finder,a)['barcode'] for a in passing_files}
    unexpected_mice = {re.search(barcode_finder,a)['barcode'] for a in unexpected_files}
    
    passing_mice = passing_mice.difference(missing_mice).difference(unexpected_mice)
    
    return passing_files, missing_files, unexpected_files, \
        passing_mice, missing_mice, unexpected_mice



#%% define class

class PandasModel(QAbstractTableModel):
    """
    A model to interface a Qt view with pandas dataframe
    
    code adapted from example located at
    https://doc.qt.io/qtforpython/examples/example_external__pandas.html
    
    """

    def __init__(self, dataframe: pandas.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe.copy()



    def rowCount(self, parent=QModelIndex()) -> int:
        """ Override method from QAbstractTableModel

        Return row count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe)

        return 0



    def columnCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

        Return column count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    
    def setData(self, index, value, role):
        if role == Qt.EditRole:
            self._dataframe.iloc[index.row(),index.column()] = value
            return True


    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        """Override method from QAbstractTableModel

        Return data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = str(self._dataframe.iloc[index.row(), index.column()])
            return value

        return None


    
    def flags(self,index):
        # presumable needed in order to provide editable table functionality
        
        # use of | performs a bitwise 'or' comparison. in this case it
        # results in creation of a Qt.ItemFlag ...
        return Qt.ItemIsSelectable|Qt.ItemIsEnabled|Qt.ItemIsEditable
    
    

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
        ):
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])
            
        return None



class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow,self).__init__()

        self.setWindowTitle('KOMP File Audit - v{}'.format(__VERSION__))
        self.setGeometry(10,10,900,750)
        self.move(100,100)
        self.Label_1=QLabel(
            '<h1>KOMP File Audit - v{}</h1>'.format(__VERSION__),
            parent=self
            )
        self.Label_1.setAlignment(Qt.AlignCenter)
        
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        
        
        self.mouse_list = pandas.DataFrame({'mouse_list':['']})
        
        self.file_list = pandas.DataFrame({'file_list':['']})
        
        self.report = {}
                
        self.KOMP_test_settings = {
            'std':self.check_std,
            'xray-faxitron':self.check_xray,
            'xray-bruker':self.check_xray,
            'body comp':self.check_body_comp,
            'echo':self.check_echo,
            'ecg':self.check_ecg
            }
        
        
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.Label_1)
        self.central_widget.setLayout(self.layout)
        
        self.upper_layout = QHBoxLayout()
        self.lower_layout = QHBoxLayout()
        self.layout.addLayout(self.upper_layout)
        self.layout.addLayout(self.lower_layout)
                
        self.controls_layout = QVBoxLayout()
        self.animal_layout = QVBoxLayout()
        self.files_layout = QVBoxLayout()
        self.upper_layout.addLayout(self.controls_layout)
        self.upper_layout.addLayout(self.animal_layout)
        self.upper_layout.addLayout(self.files_layout)
        
        self.feedback_layout = QVBoxLayout()
        self.lower_layout.addLayout(self.feedback_layout)
        
        
        # setup table for animals
        self.animal_view = QTableView(self)
        self.animal_df = PandasModel(self.mouse_list)
        # adjust aesthetics
        self.animal_view.horizontalHeader().setStretchLastSection(True)
        self.animal_view.setAlternatingRowColors(True)
        # adjust behaviors
        self.animal_view.setSelectionBehavior(QTableView.SelectRows)
        # display the data model
        self.animal_view.setModel(self.animal_df)
        self.animal_layout.addWidget(self.animal_view)


        # setup table for files
        self.file_view = QTableView(self)
        self.file_df = PandasModel(self.file_list)
        # adjust aesthetics
        self.file_view.horizontalHeader().setStretchLastSection(True)
        self.file_view.setAlternatingRowColors(True)
        # adjust behaviors
        self.file_view.setSelectionBehavior(QTableView.SelectRows)
        # display the data model
        self.file_view.setModel(self.file_df)
        self.files_layout.addWidget(self.file_view)
        # label for directory
        self.file_label = QLabel('Directory:')
        self.files_layout.addWidget(self.file_label)

        # add feedback window
        self.text1 = QTextEdit(self)
        self.text1.insertHtml(
            html_text_color(
                f'<strong><em>KOMP File Audit - VERSION {__VERSION__}</em></strong>',
                'black'
                )
            )
        self.feedback_layout.addWidget(self.text1)
        
        # add controls
        #    parse animal list
        self.parse_animal_list = QPushButton('Parse Animal List')
        self.parse_animal_list.clicked.connect(self.parse_animal_list_action)
        self.controls_layout.addWidget(self.parse_animal_list)
        #    clear animal list
        self.clear_animal_list = QPushButton('Clear Animal List')
        self.clear_animal_list.clicked.connect(self.clear_animal_list_action)
        self.controls_layout.addWidget(self.clear_animal_list)
        #    select file directory to walk
        self.select_file_directory = QPushButton('Select File Directory for Audit')
        self.select_file_directory.clicked.connect(self.select_file_directory_action)
        self.controls_layout.addWidget(self.select_file_directory)
        
        #    select settings for check
        self.KOMP_test_label = QLabel('Select KOMP Test')
        self.controls_layout.addWidget(self.KOMP_test_label)
        self.KOMP_test = QComboBox(self)
        self.KOMP_test.addItems(self.KOMP_test_settings.keys())
        self.controls_layout.addWidget(self.KOMP_test)
        self.KOMP_test.setStyleSheet('background-color: white')
        self.KOMP_test.setStyleSheet('selection-background-color: blue')
        #    run comparison
        self.run_audit = QPushButton('Run Audit')
        self.run_audit.setStyleSheet('background-color: green')
        self.run_audit.clicked.connect(self.run_audit_action)
        self.controls_layout.addWidget(self.run_audit)
        #    save report
        #    parse animal list
        self.report_label = QLabel('Report:')
        self.controls_layout.addWidget(self.report_label)
        self.save_report = QPushButton('Save Report')
        self.save_report.clicked.connect(self.save_report_action)
        self.controls_layout.addWidget(self.save_report)
        
        
        
    @pyqtSlot()
    def parse_animal_list_action(self):
        self.text1.insertHtml(
            html_text_color('attempting to parse animal list','blue')
            )
        if 'mouse_list' not in self.animal_df._dataframe.iloc[0].index:
            self.text1.insertHtml(
                html_text_color(
                    '<strong>List already appears parsed - clear and retry!</strong',
                    'red'
                    )
                )
            return
        
        raw_animal_list = self.animal_df._dataframe.iloc[0]['mouse_list']
        if len(raw_animal_list) == 0:
            self.text1.insertHtml(
                html_text_color(
                    '<strong>Nothing to parse!</strong>',
                    'red'
                    )
                )
            return

        parsed_list = []
        for r in raw_animal_list.split('\n'):
            for c in r.split('\t'):
                if c == '':
                    continue
                parsed_list.append(c)

        self.mouse_list = pandas.DataFrame(
            {'parsed_mouse_list':sorted(parsed_list)}
            )
        self.animal_df = PandasModel(self.mouse_list)
        self.animal_view.setModel(self.animal_df)
        self.animal_view.resizeColumnToContents(0)
        self.text1.insertHtml(
            html_text_color(
                f'<strong>{len(self.mouse_list)}</strong> animals found.',
                'black'
                )
            )


    
    @pyqtSlot()
    def clear_animal_list_action(self):
        self.reset_report()
        self.text1.insertHtml(
            html_text_color('clearing animal list','blue')
            )
        self.mouse_list = pandas.DataFrame({'mouse_list':['']})
        self.animal_df = PandasModel(self.mouse_list)
        self.animal_view.setModel(self.animal_df)
        self.animal_view.resizeColumnToContents(0)


        
    @pyqtSlot()
    def select_file_directory_action(self):
        self.reset_report()
        self.text1.insertHtml(
            html_text_color('selecting file directory for audit','blue')
            )
        self.selected_directory = QFileDialog.getExistingDirectory()
        self.file_label.setText(f'Directory: "{self.selected_directory}"')
        if self.selected_directory == '' or self.selected_directory is None:
            self.text1.insertHtml(
                html_text_color(
                    '<strong>No file directory selected!</strong',
                    'red'
                    )
                )
        else:
            self.text1.insertHtml(
                html_text_color(
                    f'directory selected, checking files : {self.selected_directory}',
                    'black'
                    )
                )
            self.populate_file_list()
            



    @pyqtSlot()
    def run_audit_action(self):
        self.text1.insertHtml(
            html_text_color(
                f'attempting to run audit - {self.KOMP_test.currentText()}',
                'blue'
                )
            )
        
        if self.mouse_list[self.mouse_list!=''].count()[0]!=0 and \
                self.file_list[self.file_list!=''].count()[0]!=0:
            self.KOMP_test_settings[self.KOMP_test.currentText()](
                self.KOMP_test.currentText()
                )

        else:
            self.text1.insertHtml(
                html_text_color(
                    '<strong>Missing Inputs - Audit Aborted!</strong',
                    'red'
                    )
                )

        

    @pyqtSlot()
    def save_report_action(self):
        output_path = QFileDialog.getSaveFileName(
            caption = 'Save Report',
            filter = ('Excel (*.xlsx)')
            )[0]
        
        if output_path != '' and self.report!={}:
            
            writer=pandas.ExcelWriter(output_path,engine='xlsxwriter')
            
            for k,v in self.report.items():
                pandas.DataFrame(
                    sorted(v)
                    ).to_excel(writer,k, index=False, header=False)
                
            writer.save()
            self.text1.insertHtml(
                html_text_color(
                    f'<strong>Report Saved : {output_path}</strong>',
                    'black'
                    )
                )
        else:
            self.text1.insertHtml(
                html_text_color(
                    '<strong>Unable to save report!</strong>',
                    'red'
                    )
                )
            

    def reset_report(self):
        self.report = {}
        self.report_label.setText('Report:')
    
    def build_report(
            self,
            passing_files,
            missing_files,
            unexpected_files,
            passing_mice,
            missing_mice,
            unexpected_mice
            ):
        
        self.report = {
            'passing_files':passing_files,
            'missing_files':missing_files,
            'unexpected_files':unexpected_files,
            'passing_mice':passing_mice,
            'missing_mice':missing_mice,
            'unexpected_mice':unexpected_mice
            }
        
        self.report_label.setText(f'REPORT: {self.KOMP_test.currentText()}\n{self.selected_directory}')
        
        file_total = len(passing_files) + \
            len(missing_files) + \
            len(unexpected_files)
        
        animal_total = len(passing_mice) + \
            len(missing_mice) + \
            len(unexpected_mice)
        
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Audit Results : {file_total} files checked</strong>',
                'black'
                )
            )
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Passing : {len(passing_files)} files</strong><br/>'+ \
                f'{"    ".join(sorted(passing_files))}',
                'green'
                )
            )
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Missing : {len(missing_files)} files</strong><br/>'+ \
                f'{"    ".join(sorted(missing_files))}',
                'red'
                )
            )
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Unexpected : {len(unexpected_files)} files</strong><br/>'+ \
                f'{"    ".join(sorted(unexpected_files))}',
                'orange'
                )
            )
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Audit Results : {animal_total} animals checked</strong>',
                'black'
                )
            )
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Passing : {len(passing_mice)} mice</strong><br/>'+ \
                f'{"    ".join(sorted(passing_mice))}',
                'green'
                )
            )
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Missing : {len(missing_mice)} mice</strong><br/>'+ \
                f'{"    ".join(sorted(missing_mice))}',
                'red'
                )
            )
        self.text1.insertHtml(
            html_text_color(
                f'<strong>Unexpected : {len(unexpected_mice)} mice</strong><br/>'+ \
                f'{"    ".join(sorted(unexpected_mice))}',
                'orange'
                )
            )
        
    
    
    
    def populate_file_list(self):
        file_dict = {}
        found_files = os.walk(self.selected_directory)
        for d,p,f in found_files:
            for filename in f:
                file_dict[filename] = os.path.join(d,filename)
                
        if len(file_dict) == 0:
            self.text1.insertHtml(
                html_text_color('<strong>No files found!</strong>','red')
                )
        else:
            self.text1.insertHtml(
                html_text_color(
                    f'<strong>{len(file_dict)}</strong> files found',
                    'black'
                    )
                )
            self.file_list = pandas.DataFrame(
                {
                    'filename':file_dict.keys(),
                    'path':file_dict.values()}
                )
            self.file_df = PandasModel(self.file_list)
            self.file_view.setModel(self.file_df)
            self.file_view.resizeColumnToContents(0)
           




    def check_std(self,protocol_version):
    
        file_suffixes = [
            '.csv',
            ]
                        
        
        self.build_report(
            *filename_audit(
                self.mouse_list,
                self.file_list,
                file_suffixes,
                8,
                )
            )



    def check_xray(self,protocol_version):
        if protocol_version == 'xray-bruker':
            
            file_suffixes = [
                '.bip',
                '-2.bip',
                '-h.bip',
                '-l.bip',
                '-v.bip'
                ]
                            
            
            self.build_report(
                *filename_audit(
                    self.mouse_list,
                    self.file_list,
                    file_suffixes,
                    8,
                    assignment = ['T','t','D','d']
                    )
                )
            
        elif protocol_version == 'xray-faxitron':
            file_suffixes = [
                '.dcm',
                '-2.dcm',
                '-h.dcm',
                '-l.dcm',
                '-v.dcm'
                ]
                            
            
            self.build_report(
                *filename_audit(
                    self.mouse_list,
                    self.file_list,
                    file_suffixes,
                    8,
                    assignment = ['T','t','D','d']
                    )
                )
            
            
        else:
            self.text1.insertHtml(
                html_text_color(
                    '<strong>unknown protocol version!</strong>',
                    'red'
                    )
                )



    def check_body_comp(self,protocol_version):
        file_suffixes = [
            '.txt',
            '.jpg',
            ]
                        
        
        self.build_report(
            *filename_audit(
                self.mouse_list,
                self.file_list,
                file_suffixes,
                8
                )
            )


    
    def check_echo(self,protocol_version):
        self.text1.insertHtml(
            html_text_color(
                '<strong>module not yet built - coming soon...</strong>',
                'red'
                )
            )


    
    def check_ecg(self,protocol_version):
        file_suffixes = [
            '.txt',
            '.adicht'
            ]
                        
        
        self.build_report(
            *filename_audit(
                self.mouse_list,
                self.file_list,
                file_suffixes,
                8,
                assignment = ['E','e']
                )
            )
        


    

#%% define main


def main():
    defaultfont = QtGui.QFont('Arial', 8)
    QtWidgets.QApplication.setStyle("fusion")
    QtWidgets.QApplication.setFont(defaultfont)
    app=QApplication(sys.argv)
    MW = MainWindow()
    MW.show()
    sys.exit(app.exec_())



#%% run main()

if __name__ == '__main__':
    main()