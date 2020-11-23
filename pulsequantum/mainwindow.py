

import time
from PyQt5.QtCore import QCoreApplication,Qt
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QApplication, QWidget, QFrame,QMainWindow, QPushButton, QAction, QMessageBox, QLineEdit, QLabel, QSizePolicy
from PyQt5.QtWidgets import QCheckBox,QDialog,QTableWidget,QTableWidgetItem,QVBoxLayout,QHBoxLayout,QComboBox,QGridLayout
import pickle 
import broadbean as bb
from broadbean.plotting import plotter
from awgsequencing import Sequencing

import matplotlib
matplotlib.use('QT5Agg')



#############################################################################################
#Hardcoded stuff, should incorporate into main code
#############################################################################################

nlines=3;
nchans=2;

ramp = bb.PulseAtoms.ramp; #Globally defined ramp, element, and sequence

gseq = bb.Sequence();

divch1=11.5;divch2=11.75;divch3=11.7;divch4=1; #Hardcoded channel dividers
divch=[divch1,divch2,divch3,divch4];

awgclock=1.2e9;
corrDflag=0; #Global flag: Is correction D pulse already defined in the pulse table?

#Any new parameter defined for the "Special" sequencing tab needs to go here in order to appear in the dropdown menu
params=["det","psm_load","psm_unload","psm_load_sym","psm_unload_sym","dephasing_corrD"]
 


class pulsetable(QMainWindow):
    """
    Main pulse building class and main window
    """

    def __init__(self,AWG = None):
        #super(pulseGUI, self).__init__()
        super().__init__()
        self.setGeometry(50, 50, 1100, 900)
        self.setWindowTitle('Pulse Table Panel')
        self.mainwindow=pulsetable
        self.statusBar()
        self._sequencebox=None
        self.AWG = AWG
        self.gelem = bb.Element()
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        
        self.home()

    def home(self):

        
        #Set up initial pulse table
        table=QTableWidget(4,4,self)
        table.setGeometry(50, 100, 1000, 400)
        table.setColumnCount((nchans*3)+2)
        table.setRowCount(nlines)
        
        #Set horizontal headers
        h=nchans+1;
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Time (us)"));
        table.setHorizontalHeaderItem(1, QTableWidgetItem("Ramp? 1=Yes"));
        for i in range(nchans):
            table.setHorizontalHeaderItem(i+2, QTableWidgetItem("CH%d"%(i+1)));
            table.setHorizontalHeaderItem(h+1, QTableWidgetItem("CH%dM1"%(i+1)));
            table.setHorizontalHeaderItem(h+2, QTableWidgetItem("CH%dM2"%(i+1)));
            h=h+2;
        
        
        
        #Set vertical headers
        nlist=["load", "unload", "measure"];
        for i in range(nlines):
            table.setVerticalHeaderItem(i, QTableWidgetItem(nlist[i]));
            
        #Set table items to zero initially    
        for column in range(table.columnCount()):
            for row in range(table.rowCount()):
                if column==0:
                    table.setItem(row,column, QTableWidgetItem("1"));
                else:
                    table.setItem(row,column, QTableWidgetItem("0"));

        # Create channel divider boxes and buttons
        chlabel1='Ch1';chlabel2='Ch2';chlabel3='Ch3';chlabel4='Ch4';
        chlabel=[chlabel1,chlabel2,chlabel3,chlabel4];
        for i in range(len(chlabel)):
            chlabel[i]= QLabel(self);chlabel[i].setText('Ch%d'%(i+1));chlabel[i].move(100+(50*i), 520)

        chbox1 = QLineEdit(self);chbox2 = QLineEdit(self);chbox3 = QLineEdit(self);chbox4 = QLineEdit(self);
        chbox=[chbox1,chbox2,chbox3,chbox4];
        for i in range(len(chbox)):
            chbox[i].setText('{}'.format(divch[i]));
            chbox[i].setGeometry(100+(50*i),550,40,40)
        
        #Set dividers
        divbtn = QPushButton('Set Dividers', self)
        divbtn.clicked.connect(lambda state: self.setDividers(chbox))
        divbtn.resize(divbtn.sizeHint())
        divbtn.move(300,550)

        # AWG clock ("sample rate")
        setawgclockbox = QLineEdit(self);setawgclockbox.setText('1.2');setawgclockbox.setGeometry(500,550,40,40);
        setawgclocklabel= QLabel(self);setawgclocklabel.setText('AWG Clock (GS/s)');setawgclocklabel.move(500, 520);setawgclocklabel.resize(setawgclocklabel.sizeHint())
        setawgclockbtn = QPushButton('Set AWG Clock', self);setawgclockbtn.clicked.connect(lambda state: self.setAWGClock(setawgclockbox));setawgclockbtn.move(550,550);setawgclockbtn.resize(setawgclockbtn.sizeHint())
        
        #Absolute Marker
        win = QWidget(self);
        lay= QVBoxLayout(win);lay.addStretch();lay1= QHBoxLayout();lay1.addStretch();lay2= QHBoxLayout();lay2.addStretch();
        absmarkerch=QComboBox(self);
        for i in range(len(chbox)): 
            absmarkerch.addItem('CH%dM1'%(i+1));absmarkerch.addItem('CH%dM2'%(i+1));
        absstart=QLineEdit(self);absstart.setText('0');absstart.resize(absstart.sizeHint());absstop=QLineEdit(self);absstop.setText('0');absstop.resize(absstop.sizeHint());
        abssetbtn = QPushButton('Set (us)', self);absrembtn = QPushButton('Remove All', self);abssetbtn.clicked.connect(lambda state: self.absMarkerSet(absmarkerch,absstart,absstop));absrembtn.clicked.connect(lambda state: self.absMarkerRemove(absmarkerch))
        lay.addWidget(absmarkerch);lay1.addWidget(absstart);lay1.addWidget(absstop);
        lay2.addWidget(abssetbtn);lay2.addWidget(absrembtn);lay.addLayout(lay1);lay.addLayout(lay2);
        win.move(700,530);
        win.resize(win.sizeHint());
        absmarkerbox = QCheckBox(self);absmarkerbox.move(830, 515);absmarkerbox.stateChanged.connect(lambda state: self.absMarkerWidget(absmarkerbox,win))
        absmarkerboxlabel= QLabel(self);absmarkerboxlabel.setText('Absolute Marker');absmarkerboxlabel.move(720, 520);absmarkerboxlabel.resize(absmarkerboxlabel.sizeHint())
        
        # This is the start of top left buttons
        win_puls = QWidget(self);
        lay_puls= QGridLayout(win_puls);        
        #Square Pulse
        sqpbtn = QPushButton('Square Pulse', self)
        sqpbtn.clicked.connect(lambda state:self.squarePulse(table))       
        
        #Pulse Triangle
        ptpbtn = QPushButton('Pulse Triangle', self)
        ptpbtn.clicked.connect(lambda state:self.pulseTriangle(table)) 
        
        #Spin Funnel
        sfpbtn = QPushButton('Spin Funnel', self)
        sfpbtn.clicked.connect(lambda state:self.spinFunnel(table))

        #Dephasing
        dppbtn = QPushButton('Dephasing', self)
        dppbtn.clicked.connect(lambda state:self.Dephasing(table))



        
        #Plot Element
        plotbtn = QPushButton('Plot Element', self)
        #plotbtn.resize(plotbtn.sizeHint());plotbtn.move(185, 10)
        plotbtn.clicked.connect(lambda state:self.plotElement())
        
        #Generate Element
        runbtn = QPushButton('Generate Element', self);
        #runbtn.resize(runbtn.sizeHint());runbtn.move(40, 10);
        runbtn.clicked.connect(lambda state: self.generateElement(table))
        
        #Save Element
        savebtn = QPushButton('Save Element', self)
        savebtn.clicked.connect(lambda state:self.saveElement())
        
        #Load Element
        loadbtn = QPushButton('Load Element', self)
        loadbtn.clicked.connect(lambda state: self.loadElement(table))
        
        #Populate table from Sequence
        table_from_seq = QPushButton('Element from Sequence', self);
        table_from_seq.clicked.connect(lambda state: self.from_sequence(table))
        
        lay_puls.addWidget(runbtn,0,0,1,1)
        lay_puls.addWidget(plotbtn,0,1,1,1)
        lay_puls.addWidget(savebtn,1,0,1,1)
        lay_puls.addWidget(loadbtn,1,1,1,1)
        lay_puls.addWidget(sqpbtn,2,0,1,1)        
        lay_puls.addWidget(ptpbtn,2,1,1,1)
        lay_puls.addWidget(sfpbtn,2,2,1,1)
        lay_puls.addWidget(dppbtn,1,2,1,1)
        lay_puls.addWidget(table_from_seq ,2,3,1,1)
        win_puls.move(20,5)
        win_puls.resize(win_puls.sizeHint())
        
        # This is the end of top left buttons

        #Add a channel
        whichch=QComboBox(self);whichch.move(420,10);
        for i in range(len(chbox)): 
            whichch.addItem('CH%d'%(i+1));
        addchbtn = QPushButton('Add Channel', self)
        addchbtn.clicked.connect(lambda state: self.addChannel(table,whichch))
        addchbtn.resize(addchbtn.sizeHint())
        addchbtn.move(350, 40)
        
        #Remove a channel
        remchbtn = QPushButton('Remove Channel', self)
        remchbtn.clicked.connect(lambda state: self.remChannel(table,whichch))
        remchbtn.resize(remchbtn.sizeHint())
        remchbtn.move(470, 40)
        
        #Add a pulse
        addpbtn = QPushButton('Add Pulse', self)
        whichp = QLineEdit(self);whichp.setText('Set name');whichp.setGeometry(720,15,70,20);
        addpbtn.clicked.connect(lambda state: self.addPulse(table,whichp))
        addpbtn.resize(addpbtn.sizeHint())
        addpbtn.move(660, 40)
        
        #Remove a pulse
        rempbtn = QPushButton('Remove Pulse', self)
        rempbtn.clicked.connect(lambda state: self.remPulse(table,whichp))
        rempbtn.resize(rempbtn.sizeHint())
        rempbtn.move(760, 40)
        
        #Rename a pulse
        renamepbtn = QPushButton('Rename Pulse', self);renamepbtn.resize(renamepbtn.sizeHint());renamepbtn.move(910, 40)
        oldpname = QLineEdit(self);oldpname.setText('Old name');oldpname.setGeometry(890,15,70,20);
        newpname = QLineEdit(self);newpname.setText('New name');newpname.setGeometry(965,15,70,20);
        renamepbtn.clicked.connect(lambda state: self.renamePulse(table,oldpname,newpname))
        
        #Remove a pulse
        rempbtn = QPushButton('Remove Pulse', self)
        rempbtn.clicked.connect(lambda state: self.remPulse(table,whichp))
        rempbtn.resize(rempbtn.sizeHint())
        rempbtn.move(760, 40)
        
        
        #Correction D
        corrbtn = QPushButton('Correction D', self)
        corrbtn.clicked.connect(lambda state: self.correctionD(table))
        corrbtn.resize(corrbtn.sizeHint())
        corrbtn.move(100, 600)

         

        #Sequence and upload
        seqbtn = QPushButton('Upload Sequence', self)
        seqbtn.clicked.connect(lambda state:self.sequence())
        seqbtn.resize(seqbtn.sizeHint())
        seqbtn.move(400, 600)

        
        
        
        
        
        self.show()
        win.hide()
        
        
    def generateElement(self,table):
        #Make element from pulse table
        self.gelem= bb.Element();
        h=int((table.columnCount()-2)/3);
        prevlvl=0;
        global awgclock;
        v=table.rowCount();
        for col in range(2,h+2):
            chno=int(table.horizontalHeaderItem(col).text()[2]);
            gp = bb.BluePrint()
            gp.setSR(awgclock);
            for row in range(v):
                nm=table.verticalHeaderItem(row).text();
                dr=(float(table.item(row,0).text()))*1e-6;
                rmp=int(table.item(row,1).text());
                lvl=(float(table.item(row,col).text()))*divch[col-2]*1e-3;
                mkr1=int(table.item(row,h+2).text());
                mkr2=int(table.item(row,h+3).text());
                if rmp==0:
                    gp.insertSegment(row, ramp, (lvl, lvl), name=nm, dur=dr);
                if rmp==1:
                    if row==0:
                        gp.insertSegment(row, ramp, (0, lvl), name=nm, dur=dr);
                    else:
                        gp.insertSegment(row, ramp, (prevlvl, lvl), name=nm, dur=dr);
                if mkr1==1:
                    gp.setSegmentMarker(nm, (0,dr), 1);
                if mkr2==1:
                    gp.setSegmentMarker(nm, (0,dr), 2);
                prevlvl=lvl;
            self.gelem.addBluePrint(chno, gp);
            h=h+2;
        self.gelem.validateDurations();
        
    def plotElement(self):
        plotter(self.gelem);
    

#############################################################################################
# Saving and loading of element does not work yet. Using it may crash the GUI. I tried to use
# pickle for saving an element object, however this created tons of problems I wasn't able to
# solve. If I had to do it again, I would drill down into the dictionaries to save and load.
#############################################################################################
    def saveElement(self):
        savedict=self.gelem.getArrays(includetime=True);
        dlg=QFileDialog(self);
        fileName, _ =  dlg.getSaveFileName(self,"Save Element",r"A:\Users\fabio\QCoDeSLocal\SpinQubit\Pulse_wrappers\Pulsinglibrary");
        with open(fileName, 'wb') as f:
            pickle.dump(savedict,f,protocol=pickle.HIGHEST_PROTOCOL)
    
    def addChannel(self,table,whichch):
        global nchans;
        nchans=nchans+1;
        index=whichch.currentIndex();
        ch=[1,2,3,4];chno=ch[index];
        n=table.columnCount();nchan=int((table.columnCount()-2)/3);
        table.insertColumn(nchan+2);table.insertColumn(n+1);table.insertColumn(n+2);
        table.setHorizontalHeaderItem(nchan+2, QTableWidgetItem("CH%d"%chno));
        table.setHorizontalHeaderItem(n+1, QTableWidgetItem("CH%dM1"%chno));
        table.setHorizontalHeaderItem(n+2, QTableWidgetItem("CH%dM2"%chno));
        for row in range(table.rowCount()):
            table.setItem(row,nchan+2, QTableWidgetItem("0"));
            table.setItem(row,n+1, QTableWidgetItem("0"));
            table.setItem(row,n+2, QTableWidgetItem("0"));
    
    def remChannel(self,table,whichch):
        global nchans;
        nchans=nchans-1;
        n=table.columnCount();
        n=n-1;
        for i in range(n):
            temp=str(whichch.currentText());
            if str(table.horizontalHeaderItem(i).text())==temp:
                table.removeColumn(i);
            if str(table.horizontalHeaderItem(i).text())==temp+"M1":    
                table.removeColumn(i);
            if str(table.horizontalHeaderItem(i).text())==temp+"M2":
                table.removeColumn(i);
    
    def addPulse(self,table,whichp,i=-1):
        global nlines;
        nlines=nlines+1;
        if i==-1:
            n=table.rowCount();
        else:
            n=i;
        table.insertRow(n);
        table.setVerticalHeaderItem(n,QTableWidgetItem(whichp.text()));
        for column in range(table.columnCount()):
            if column==0:
                table.setItem(n,column, QTableWidgetItem("1"));
            else:
                table.setItem(n,column, QTableWidgetItem("0"));
    
    def remPulse(self,table,whichp):
        global nlines;
        global corrDflag;
        nlines=nlines-1;
        for n in range(table.rowCount()):
            if table.verticalHeaderItem(n).text()==whichp.text():
                if whichp.text()=='corrD':
                    corrDflag=0;
                table.removeRow(n);
    
    def renamePulse(self,table,oldpname,newpname):
        for n in range(table.rowCount()):
            if table.verticalHeaderItem(n).text()==oldpname.text():
                table.setVerticalHeaderItem(n,QTableWidgetItem(newpname.text()));
    
    
        
    def setDividers(self,chbox):
        for i in range(len(divch)):
            divch[i]=(float(chbox[i].text()));
        
    def setAWGClock(self,setawgclockbox):
        global awgclock;
        awgclock=(float(setawgclockbox.text()))*1e9;
        
    def absMarkerWidget(self,absmarkerbox,win):
        if absmarkerbox.isChecked():
            win.show()
        else:
            win.hide()
    
    def absMarkerSet(self,absmarkerch,absstart,absstop):
        tempbp=bb.BluePrint();
        mstart=(float(absstart.text())*1e-6);
        mstop=(float(absstop.text())*1e-6);
        index=absmarkerch.currentIndex();
        ch=[1,1,2,2,3,3,4,4];chno=ch[index];
        mno=[1,2,1,2,1,2,1,2];m=mno[index];
        tempbp=self.gelem._data[chno]['blueprint'];
        if m==1:
            tempbp.marker1=[(mstart,mstop)];
        if m==2:
            tempbp.marker2=[(mstart,mstop)];
        self.gelem._data[chno]['blueprint']=tempbp;
    
    def absMarkerRemove(self,absmarkerch):
        tempbp=bb.BluePrint();
        index=absmarkerch.currentIndex();
        ch=[1,1,2,2,3,3,4,4];chno=ch[index];
        mno=[1,2,1,2,1,2,1,2];m=mno[index];
        tempbp=self.gelem._data[chno]['blueprint'];
        if m==1:
            tempbp.marker1=[];
        if m==2:
            tempbp.marker2=[];
        self.gelem._data[chno]['blueprint']=tempbp;
        
        
#############################################################################################
# The correction D pulse keeps the centre of gravity of the pulse at the DC value (voltage
# seen by the same when there is no pulsing. Not always used or needed.
#############################################################################################
    def correctionD(self,table):
        global awgclock;
        global corrDflag;
        if corrDflag==1:
            print("Correction D pulse already exists.")
            return;
        corrDflag=1;
        awgclockinus=awgclock/1e6;
        dpulse = QLineEdit(self);dpulse.setText('corrD');
        tottime=0;
        dpos=1;#position of correction D pulse, hardcoded for now
        self.addPulse(table,dpulse,dpos);
        #Set D pulse time to 60% of total pulse cycle time
        for row in range(table.rowCount()):
            nm=table.verticalHeaderItem(row).text();
            if nm!='corrD':
                tottime=tottime+(float(table.item(row,0).text()));
        timeD=round(tottime/1.65*(awgclockinus))/awgclockinus;
        table.setItem(dpos,0, QTableWidgetItem("%f"%timeD));
        
        #Correct all voltages in a loop
        for column in range(6):
            tottimevolt=0;
            colnm=table.horizontalHeaderItem(column).text();
            for row in range(table.rowCount()):
                rownm=table.verticalHeaderItem(row).text();
                rmp=int(table.item(row,1).text());
                if (rownm!='corrD') and (colnm=='CH1' or colnm=='CH2' or colnm=='CH3' or colnm=='CH4'):
                    if rmp==0:
                        tottimevolt=tottimevolt+((float(table.item(row,0).text()))*(float(table.item(row,column).text())));
                    if rmp==1:
                        if row==0:
                            tottimevolt=tottimevolt+((float(table.item(row,0).text()))*(float(table.item(row,column).text()))/2);
                        else:
                            tottimevolt=tottimevolt+((float(table.item(row,0).text()))*((float(table.item(row,column).text()))+(float(table.item(row-1,column).text())))/2);
                voltD=-tottimevolt/timeD;
            if (column!=0) and (column!=1) and (colnm=='CH1' or colnm=='CH2' or colnm=='CH3' or colnm=='CH4'):
                table.setItem(dpos,column, QTableWidgetItem("%f"%voltD));
            


#############################################################################################
# Saving and loading of element does not work yet. Using it may crash the GUI. I tried to use
# pickle for saving an element object, however this created tons of problems I wasn't able to
# solve. If I had to do it again, I would drill down into the dictionaries to save and load.
#############################################################################################    
    def loadElement(self,table):
        global awgclock;
        dlg=QFileDialog(self);
        fileName, _ =  dlg.getOpenFileName(self,"Load Element",r"A:\Users\fabio\QCoDeSLocal\SpinQubit\Pulse_wrappers\Pulsinglibrary");
        with open(fileName, 'rb') as f:
            loaddict=pickle.load(f)
        table.setRowCount(0);
        table.setColumnCount(0);
        #Create the element
        chno=list(loaddict.keys());#List of channels
        for i in range(len(chno)):
            temp=loaddict[chno[i]];
            wfm=temp['wfm'];
            newdurations=temp['newdurations'];
            m1=temp['m1'];
            m2=temp['m2'];
            time=temp['time'];
#            print(len(newdurations));print(len(wfm));
            kwargs={'m1':m1,'m2':m2,'time':time};
            gelem.addArray(chno[i],wfm,awgclock,**kwargs);
       # Generate the pulse table

    
    def sequence(self):
        if self._sequencebox is None:
            self._sequencebox = Sequencing(self.AWG,self.gelem);
            self._sequencebox.exec_();
        else:
#            global_point = callWidget.mapToGlobal(point)
#            self._sequencebox.move(global_point - QtCore.QPoint(self.width(), 0))
             self.SetForegroundWindow(self._sequencebox)
    
    def close_application(self):

        choice = QMessageBox.question(self, 'Message',
                                     "Are you sure to quit?", QMessageBox.Yes |
                                     QMessageBox.No, QMessageBox.No)

        if choice == QMessageBox.Yes:
            print('quit application')
            app.exec_()
        else:
            pass




#############################################################################################
# A few hardcoded pulses that we use over and over, and some placeholder buttons.
#############################################################################################

    def squarePulse(self,table):
        table.setColumnCount((2*3)+2);
        table.setRowCount(2);
        #Set horizontal headers
        h=nchans+1;
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Time (us)"));
        table.setHorizontalHeaderItem(1, QTableWidgetItem("Ramp? 1=Yes"));
        for i in range(2):
            table.setHorizontalHeaderItem(i+2, QTableWidgetItem("CH%d"%(i+1)));
            table.setHorizontalHeaderItem(h+1, QTableWidgetItem("CH%dM1"%(i+1)));
            table.setHorizontalHeaderItem(h+2, QTableWidgetItem("CH%dM2"%(i+1)));
            h=h+2;
        
        #Set vertical headers
        nlist=["up", "down"];
        for i in range(2):
            table.setVerticalHeaderItem(i, QTableWidgetItem(nlist[i]));
            
        #Set table items to zero initially    
        for column in range(table.columnCount()):
            for row in range(table.rowCount()):
                if column==0:
                    table.setItem(row,column, QTableWidgetItem("1"));
                else:
                    table.setItem(row,column, QTableWidgetItem("0"));
        table.setItem(1,4, QTableWidgetItem("1"));
        table.setItem(1,5, QTableWidgetItem("1"));


    def pulseTriangle(self,table):
        table.setColumnCount((2*3)+2)
        table.setRowCount(4)
        
        #Set horizontal headers
        h=nchans+1;
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Time (us)"));
        table.setHorizontalHeaderItem(1, QTableWidgetItem("Ramp? 1=Yes"));
        for i in range(nchans):
            table.setHorizontalHeaderItem(i+2, QTableWidgetItem("CH%d"%(i+1)));
            table.setHorizontalHeaderItem(h+1, QTableWidgetItem("CH%dM1"%(i+1)));
            table.setHorizontalHeaderItem(h+2, QTableWidgetItem("CH%dM2"%(i+1)));
            h=h+2;
        
        #Set vertical headers
        nlist=["unload", "load","separate", "measure"];
        #nlist=["detuning_up", "detuning_up_b","down", "down_b"];
        for i in range(4):
            table.setVerticalHeaderItem(i, QTableWidgetItem(nlist[i]));
            
        #Set table items to zero initially    
        for column in range(table.columnCount()):
            for row in range(table.rowCount()):
                if column==0:
                    table.setItem(row,column, QTableWidgetItem("20"));
                else:
                    table.setItem(row,column, QTableWidgetItem("0"));
        for column in range(table.columnCount()):
            table.setItem(3,4, QTableWidgetItem("1"));
        table.setItem(0,2, QTableWidgetItem("-8.8"));
        table.setItem(0,3, QTableWidgetItem("-6"));
        table.setItem(1,2, QTableWidgetItem("-6.8"));
        table.setItem(1,3, QTableWidgetItem("2"));
        table.setItem(2,2, QTableWidgetItem("10.2"));
        table.setItem(2,3, QTableWidgetItem("-4"));
        table.setItem(3,2, QTableWidgetItem("0"));
        table.setItem(3,3, QTableWidgetItem("0"));
        
        # From Sequence
    def from_sequence(self,table):
         
        seq_description = gseq.description['1']['channels']
        seg_name = []
        seg_durations = []
        seg_ramp = []
        values = []
        marker1 = []
        marker2 = []
        for chan in seq_description.keys():
            ch_values = []
            channels_marker1 = []
            channels_marker2 = []
            print(chan)
            marker1_rel = seq_description[chan]['marker1_rel']
            marker2_rel = seq_description[chan]['marker2_rel']
            seg_mar_list = list(seq_description[chan].keys())
            seg_list = [s for s in seg_mar_list if 'segment' in s]
            for i, seg in enumerate(seg_list):
                seg_digt = seq_description[chan][seg]
                tmp_name = seg_digt['name']
                tmp_durations = seg_digt["durations"]
                if tmp_name not in seg_name:
                    seg_name.append(tmp_name)
                    seg_durations.append(tmp_durations)
                    if seg_digt['arguments']['start'] != seg_digt['arguments']['stop']:
                        seg_ramp.append(1)
                    else:
                        seg_ramp.append(0)
                ch_values.append(seg_digt['arguments']['stop'])
                if marker1_rel[i] == (0,0):
                    channels_marker1.append(0)
                else:
                    channels_marker1.append(1)
                    
                if marker2_rel[i] == (0,0):
                    channels_marker2.append(0)
                else:
                    channels_marker2.append(1)             
            values.append(ch_values)
            marker1.append(channels_marker1)
            marker2.append(channels_marker2)
         
        nchans = len(values)
        nsegs = len(values[0])


        table.setColumnCount((nchans*3)+2)
        table.setRowCount(nsegs)
        
        #Set horizontal headers
        h=nchans+1;
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Time (us)"));
        table.setHorizontalHeaderItem(1, QTableWidgetItem("Ramp? 1=Yes"));
        for i in range(nchans):
            table.setHorizontalHeaderItem(i+2, QTableWidgetItem("CH%d"%(i+1)));
            table.setHorizontalHeaderItem(h+1, QTableWidgetItem("CH%dM1"%(i+1)));
            table.setHorizontalHeaderItem(h+2, QTableWidgetItem("CH%dM2"%(i+1)));
            h=h+2;
        
        #Set vertical headers
        #nlist= seg_name
        for i, name in enumerate(seg_name):
            table.setVerticalHeaderItem(i, QTableWidgetItem(name));
            
        
        for seg in range(nsegs):
            duration = str(seg_durations[seg]/1e-6)
            table.setItem(seg,0, QTableWidgetItem(duration))
            ramp_yes = str(seg_ramp[seg])
            table.setItem(seg,0, QTableWidgetItem(duration))
            table.setItem(seg,1, QTableWidgetItem(ramp_yes))
            for ch in range(nchans):
               val = str(values[ch][seg]/(divch[ch]*1e-3))
               mark1 = str(marker1[ch][seg])
               mark2 = str(marker2[ch][seg])
               table.setItem(seg,ch+2, QTableWidgetItem(val))
               table.setItem(seg,ch*2+4, QTableWidgetItem(mark1))
               table.setItem(seg,ch*2+5, QTableWidgetItem(mark2))

        
        
    def spinFunnel(self,table):
        table.setColumnCount((2*3)+2)
        table.setRowCount(8)
        
        #Set horizontal headers
        h=nchans+1;
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Time (us)"));
        table.setHorizontalHeaderItem(1, QTableWidgetItem("Ramp? 1=Yes"));
        for i in range(nchans):
            table.setHorizontalHeaderItem(i+2, QTableWidgetItem("CH%d"%(i+1)));
            table.setHorizontalHeaderItem(h+1, QTableWidgetItem("CH%dM1"%(i+1)));
            table.setHorizontalHeaderItem(h+2, QTableWidgetItem("CH%dM2"%(i+1)));
            h=h+2;
        
        #Set vertical headers
        nlist=["start","unload", "load","reference","wait","separate", "measure","stop"];
        for i in range(8):
            table.setVerticalHeaderItem(i, QTableWidgetItem(nlist[i]));
            
        #Set table items to zero initially    
        for column in range(table.columnCount()):
            for row in range(table.rowCount()):
                table.setItem(row,column, QTableWidgetItem("0"));
        
        #Times
        table.setItem(0,0, QTableWidgetItem("0.01"));
        table.setItem(1,0, QTableWidgetItem("20"));
        table.setItem(2,0, QTableWidgetItem("20"));
        table.setItem(3,0, QTableWidgetItem("10"));
        table.setItem(4,0, QTableWidgetItem("1"));
        table.setItem(5,0, QTableWidgetItem("0.5"));
        table.setItem(6,0, QTableWidgetItem("10"));
        table.setItem(7,0, QTableWidgetItem("0.01"));
        
        #Markers
        table.setItem(6,4, QTableWidgetItem("1"));
        table.setItem(3,4, QTableWidgetItem("1"));
        
        #Pulses
        table.setItem(1,2, QTableWidgetItem("-8.8"));
        table.setItem(1,3, QTableWidgetItem("-6"));
        table.setItem(2,2, QTableWidgetItem("-6.8"));
        table.setItem(2,3, QTableWidgetItem("2"));
        table.setItem(5,2, QTableWidgetItem("9.8"));
        table.setItem(5,3, QTableWidgetItem("-2"));
        
    def Dephasing(self,table):
        table.setColumnCount((2*3)+2)
        table.setRowCount(5)
        
        #Set horizontal headers
        h=nchans+1;
        table.setHorizontalHeaderItem(0, QTableWidgetItem("Time (us)"));
        table.setHorizontalHeaderItem(1, QTableWidgetItem("Ramp? 1=Yes"));
        for i in range(nchans):
            table.setHorizontalHeaderItem(i+2, QTableWidgetItem("CH%d"%(i+1)));
            table.setHorizontalHeaderItem(h+1, QTableWidgetItem("CH%dM1"%(i+1)));
            table.setHorizontalHeaderItem(h+2, QTableWidgetItem("CH%dM2"%(i+1)));
            h=h+2;
        
        #Set vertical headers
        nlist=["dummy","Prepare","Prepare*","Separate","Measure"];
        for i in range(5):
            table.setVerticalHeaderItem(i, QTableWidgetItem(nlist[i]));
            
        #Set table items to zero initially    
        for column in range(table.columnCount()):
            for row in range(table.rowCount()):
                table.setItem(row,column, QTableWidgetItem("0"));
        
        #Times
        table.setItem(0,0, QTableWidgetItem("5000"));
        table.setItem(1,0, QTableWidgetItem("200"));
        table.setItem(2,0, QTableWidgetItem("25"));
        table.setItem(3,0, QTableWidgetItem("2000"));
        table.setItem(4,0, QTableWidgetItem("10"));
        # table.setItem(5,0, QTableWidgetItem("0.5"));
        # table.setItem(6,0, QTableWidgetItem("10"));
        # table.setItem(7,0, QTableWidgetItem("0.01"));
        
        #Markers
        table.setItem(4,4, QTableWidgetItem("1"));
        # table.setItem(3,4, QTableWidgetItem("1"));
        
        #Pulses: (n,m): n - row from 0, m - clmn from 0
        #Prepare 
        table.setItem(1,2, QTableWidgetItem("-4.077"));
        table.setItem(1,3, QTableWidgetItem("4.5322"));
        #Prepare* 
        table.setItem(2,2, QTableWidgetItem("0"));
        table.setItem(2,3, QTableWidgetItem("0"));
        #Separate 
        table.setItem(3,2, QTableWidgetItem("6.604"));
        table.setItem(3,3, QTableWidgetItem("-3.0405"));
        #Measure 
        table.setItem(4,2, QTableWidgetItem("0"));
        table.setItem(4,3, QTableWidgetItem("0"));        

        
#############################################################################################
###################            SET PULSE PARAMETER          #################################
#############################################################################################

    def setpulseparameter(elem,param,value):
        #Define your own parameters here! For setting a segment name use setpulse()
        ch=0;
        if param[0]=='N':
            ch=int(param[7]);
            seg=param[9:len(param)];
            if param[2:6]=="Time":
                setpulseduration(elem,ch,seg,value);
            else:
                setpulselevel(elem,ch,seg,value);
        if param=='det':
            setpulselevel(elem,1,'separate',value*0.8552);#For 20-11
            setpulselevel(elem,2,'separate',-value*0.5183);#For 20-11
            #setpulselevel(elem,1,'separate',value*0.9558);#For 40-31
            #setpulselevel(elem,2,'separate',-value*0.2940);#For 40-31
            
        if param=='psm':
            setpulselevel(elem,1,'detuning',value*0.8);
            setpulselevel(elem,2,'detuning',-value*0.5);
    ##detuning load        
    #    if param=='psm_load':
    #        alpha_x = -0.6597
    #        beta_y = 0.7516
    #        setpulselevel(elem,1,'detuning_up',value*(1)*alpha_x); #BNC43
    #        setpulselevel(elem,2,'detuning_up',value*(1)*beta_y); #BNC17
    #        setpulselevel(elem,1,'detuning_up_b',value*(1)*alpha_x); #BNC43
    #        setpulselevel(elem,2,'detuning_up_b',value*(1)*beta_y); #BNC17

        if param=='dephasing_corrD':
            corrD_K0 = -1.8102
            corrD_K1 = 0.44531
            corrD_K2 = 0.0004064
            corrD_K3 = -1.0403e-7
            
            corrD_X = corrD_K0 + corrD_K1*value + corrD_K2*value*value + corrD_K3*value*value*value
            corrD_y = corrD_K0 + corrD_K1*value + corrD_K2*value*value + corrD_K3*value*value*value

            #corr amplitudes for 2ms separation
            # corrD_amp_BNC12 = -7.3569
            # corrD_amp_BNC17 = 3.07129
            setpulseduration(elem,1,'corrD', corrD_X)
            setpulseduration(elem,2,'corrD', corrD_Y)
            setpulseduration(elem,1,'Separate',value)
            setpulseduration(elem,2,'Separate',value)



    #detuning load        
        if param=='psm_load':
            alpha_x = -0.621
            beta_y = 0.7838
            setpulselevel(elem,1,'detuning_up',value*(1)*alpha_x); #BNC43
            setpulselevel(elem,2,'detuning_up',value*(1)*beta_y); #BNC17
            setpulselevel(elem,1,'detuning_up_b',value*(1)*alpha_x); #BNC43
            setpulselevel(elem,2,'detuning_up_b',value*(1)*beta_y); #BNC17

    #detuning load symmetric       
        if param=='psm_load_sym':
            alpha_x = 0.974
            beta_y = -0.226
            setpulselevel(elem,1,'detuning_up',value*(0.5)*alpha_x); #BNC12
            setpulselevel(elem,2,'detuning_up',value*(0.5)*beta_y); #BNC17
            setpulselevel(elem,1,'detuning_up_b',value*(0.5)*alpha_x); #BNC12
            setpulselevel(elem,2,'detuning_up_b',value*(0.5)*beta_y); #BNC17
            setpulselevel(elem,1,'down',value*(-0.5)*alpha_x); #BNC12
            setpulselevel(elem,2,'down',value*(-0.5)*beta_y); #BNC17
            setpulselevel(elem,1,'down_b',value*(-0.5)*alpha_x); #BNC12
            setpulselevel(elem,2,'down_b',value*(-0.5)*beta_y); #BNC17        
            
            


    #detuning unload symmetric       
        if param=='psm_unload_sym':
            alpha_x = 0.4832
            beta_y = -0.8755
            setpulselevel(elem,1,'detuning_up',value*(0.5)*alpha_x); #BNC43
            setpulselevel(elem,2,'detuning_up',value*(0.5)*beta_y); #BNC17
            setpulselevel(elem,1,'detuning_up_b',value*(0.5)*alpha_x); #BNC43
            setpulselevel(elem,2,'detuning_up_b',value*(0.5)*beta_y); #BNC17
            setpulselevel(elem,1,'down',value*(-0.5)*alpha_x); #BNC43
            setpulselevel(elem,2,'down',value*(-0.5)*beta_y); #BNC17
            setpulselevel(elem,1,'down_b',value*(-0.5)*alpha_x); #BNC43
            setpulselevel(elem,2,'down_b',value*(-0.5)*beta_y); #BNC17     
            
            
            
                    
    #detuning unload        
        if param=='psm_unload':
            alpha_x = 0.6761
            beta_y = -0.7368
            setpulselevel(elem,1,'detuning_up',value*(1)*alpha_x); #BNC43
            setpulselevel(elem,2,'detuning_up',value*(1)*beta_y); #BNC17
            setpulselevel(elem,1,'detuning_up_b',value*(1)*alpha_x); #BNC43
            setpulselevel(elem,2,'detuning_up_b',value*(1)*beta_y); #BNC17
                    

                


    #############################################################################################
    ###################    CHANGE PULSE LEVEL OR DURATION       #################################
    #############################################################################################
    def setpulselevel(elem,ch,seg,lvl,div=11.7):
        #Change a pulse within an element
        lvl=lvl*divch[ch-1]*1e-3;
    #    print(lvl);
        elem.changeArg(ch,seg,0,lvl,False);
        elem.changeArg(ch,seg,1,lvl,False);

    def setpulseduration(elem,ch,seg,dur):
        dur=dur*1e-6;
        ch=self.gelem.channels;
        for i in range(len(ch)):
            elem.changeDuration(ch[i],seg,dur,False);

    #############################################################################################
    ###################            correctionD Pulse            #################################
    #############################################################################################
    def correctionDelem(elem):
        global awgclock;
        global corrDflag;
        
        
        #If no correctionD pulse exists print error and just return
        if(corrDflag==0):
            return
        #Set up variables
        start=[];
        stop=[];
        ramp=[];
        name=[];
        seg_dur=[];
        tottime=0;
        awgclockinus=awgclock/1e6;
        
        
        #Number of pulses in element
        num=len(elem.description['{}'.format(elem.channels[0])])-4
        chs=len(elem.channels)
        #Get all pulses in element
        for j in range(chs):
            #Reinitialise pulses and total time
            start=[];stop=[];ramp=[];name=[];seg_dur=[];
            tottime=0;
            tottimevolt=0;
            timeD=0;voltD=0;
            #Get all pulses for that channel
            for i in range(num):
                pulsestart=1e3*(elem.description['{}'.format(j+1)]['segment_%02d'%(i+1)]['arguments']['start'])/divch[j+1]
                pulsestop=1e3*(elem.description['{}'.format(j+1)]['segment_%02d'%(i+1)]['arguments']['stop'])/divch[j+1] #Need correct channel dividers!
                start.append(pulsestart)
                stop.append(pulsestop)
                if(pulsestart==pulsestop):
                    ramp.append(0);
                else:
                    ramp.append(1);
                pulsedur=1e6*elem.description['{}'.format(j+1)]['segment_%02d'%(i+1)]['durations']
                seg_dur.append(pulsedur)
                pulsename=elem.description['{}'.format(j+1)]['segment_%02d'%(i+1)]['name']
                name.append(pulsename)
                #Add duration to total time
                if pulsename!='corrD':
                    tottime=tottime+pulsedur; #In us  
            #Calculate correctionD time, 65% of the total pulse cycle time
            timeD=round(tottime/1.65*(awgclockinus))/awgclockinus;
            setpulseduration(elem,j+1,'corrD',timeD);
            #Calculate tottimevolt
            for i in range(num):
                if name[i]!='corrD':
                    if(ramp[i]==0):
                        tottimevolt=tottimevolt+(start[i]*seg_dur[i]); #If not ramp take start or stop
                    if(ramp[i]==1):
                        tottimevolt=tottimevolt+(((start[i]+stop[i])/2)*seg_dur[i]); #If ramp take midpoint of start and stop
            #Calculate correctionD for that channel
            voltD=-tottimevolt/timeD;
            #Change level of correctionD pulse
            setpulselevel(elem,j+1,'corrD',voltD)