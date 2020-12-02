import broadbean as bb
import time
class Gseq():
    """
    Class for sequencing 
    """

    def __init__(self, AWG, gelem):
        self.AWG = AWG
        self.gelem = gelem
        self.gseq = bb.Sequence()

    def loadSequence(self, pathseq):
        """
        Loads af sequence from as json file
        """
        self.gseq = bb.Sequence.init_from_json(pathseq)
    
    def changedSeqTable(self, seqtable):
        """
         Updates gseg from seqtable
        """
        if self.gseq.points == 0:
            return
        for i in range(seqtable.rowCount()):
            seqlist = []
            for j in range(4):
                seqlist.append(int(seqtable.item(i, j).text()))
            self.updategseq(i, seqlist)   
            
    def updategseq(self, row, seqlist):
        """
        Updates the repetition pattern of the sequence  
        """
        self.gseq.setSequencingTriggerWait(row+1, seqlist[0])
        self.gseq.setSequencingNumberOfRepetitions(row+1, seqlist[1])
        self.gseq.setSequencingEventJumpTarget(row+1, seqlist[2])
        self.gseq.setSequencingGoto(row+1, seqlist[3])
    
    def buildSequenceWrap(self, chbox, offbox, contseqbox, timevoltbox, whichpulse, sparambox, seqstart, seqstop, seqpts):
        """
        Build gseq from gelem
        """
        self.gseq= bb.Sequence()
        timevolt=str(timevoltbox.currentText())
        whichp=str(whichpulse.text())
        sparam=str(sparambox.currentText())
        sstart=float(seqstart.text())
        sstop=float(seqstop.text())
        spts=int(seqpts.text())
        if timevolt=="Time":
            newparam="N-"+timevolt+"-0-"+whichp
        else:
            newparam="N-"+"Volt"+"-"+timevolt[2]+"-"+whichp
        self.gseq.setSR(self.gelem.SR)

        if contseqbox.isChecked():
            self.gseq.addElement(1, self.gelem)
            self.gseq.setSequencingTriggerWait(1, 0)
            self.gseq.setSequencingNumberOfRepetitions(1, 0)
            self.gseq.setSequencingEventJumpTarget(1, 0)
            self.gseq.setSequencingGoto(1, 0)
            for chan in self.gseq.channels:
                self.gseq.setChannelAmplitude(chan, (float(chbox[chan-1].text())))
                self.gseq.setChannelOffset(chan, (float(offbox[chan-1].text())))
            return
        elif sparam!="-Special-":
            buildsequencetable(self.gelem, sparam, sstart, sstop, spts)
        else:
            buildsequencetable(self.gelem, newparam, sstart, sstop, spts)
          
        for chan in self.gseq.channels:
            self.gseq.setChannelAmplitude(chan,(float(chbox[chan-1].text())))
            self.gseq.setChannelOffset(chan,(float(offbox[chan-1].text())))  


    def filterCorrection(self,hfiltbox,lfiltbox):
        if self.gseq.points==0:
            print("No sequence defined")
            return
        hptau=(float(hfiltbox.text()))*1e-6
        for i in range(4):
            self.gseq.setChannelFilterCompensation(i+1,'HP',order=1,tau=hptau)

    def buildsequencetable(elem,param,start,stop,points):
        self.gseq.setSR(elem.SR);
        value=np.linspace(start,stop,points);
        #if first letter is "N"
        #if second word is time
        #setpulseduration
        #if second word is volt
        #setpulselevel
        for n in range(points):
            setpulseparameter(elem,param,value[n]); # tjek 
            correctionDelem(elem);  # tjek
            self.gseq.addElement(n+1, elem);
            self.gseq.setSequenceSettings(n+1,0,1,0,0);
            # Arguments are position, wait for trigger (0 means OFF), number of repetitions 
            #(0 is infinite, 1 is one), jump target (0 is off), goto (0 means next)
        self.gseq.setSequenceSettings(n+1,0,1,0,1);                
               
#############################################################################################
# AWG functions (uploading, running AWG, turning on outputs. Note that in this section 
# the AWG name is hardcoded. Probably first thing that needs to be changed.
#############################################################################################
    def uploadToAWG(self,Choose_awg,chbox):
        if Choose_awg == 'AWG5014':
            #for i,  chan in enumerate(self.gseq.channels):
            #    self.AWG.channels[chan].AMP(float(chbox[chan-1].text()))
            self.AWG.ch1_amp(float(chbox[0].text()))
            self.AWG.ch2_amp(float(chbox[1].text()))
            self.AWG.ch3_amp(float(chbox[2].text()))
            self.AWG.ch4_amp(float(chbox[3].text()))
            package = self.gseq.outputForAWGFile()
            start_time=time.time();
            self.AWG.make_send_and_load_awg_file(*package[:])
            print("Sequence uploaded in %s seconds" %(time.time()-start_time));
        elif Choose_awg == 'AWG5208':
            self.gseq.name = 'sequence_from_gui'
            self.AWG.mode('AWG')
            for chan in self.gseq.channels:
                self.AWG.channels[chan-1].resolution(12)
                self.AWG.channels[chan-1].awg_amplitude(0.5)
                self.gseq.setChannelAmplitude(chan, self.AWG.channels[chan-1].awg_amplitude())
            self.AWG.clearSequenceList()
            self.AWG.clearWaveformList()
            self.AWG.sample_rate(self.gseq.SR)
            self.AWG.sample_rate(self.gseq.SR)
            
            seqx_input = self.gseq.outputForSEQXFile()
            start_time=time.time();
            seqx_output = self.AWG.makeSEQXFile(*seqx_input)
            # transfer it to the awg harddrive
            self.AWG.sendSEQXFile(seqx_output, 'sequence_from_gui.seqx')
            self.AWG.loadSEQXFile('sequence_from_gui.seqx')
            #time.sleep(1.300)
            for i,  chan in enumerate(self.gseq.channels):       
                self.AWG.channels[chan-1].setSequenceTrack('sequence_from_gui', i+1)
                self.AWG.channels[chan-1].state(1)
            print("Sequence uploaded in %s seconds" %(time.time()-start_time));
 
        else:
            print('Choose an AWG model')
  
        
    def runAWG(self,Choose_awg):
        if Choose_awg == 'AWG5014':
            if self.AWG.get_state()=='Idle':
                self.AWG.run();
                print("AWGs Running");
            elif self.AWG.get_state()=='Running':
                self.AWG.stop();
                print("AWGs Stopped");
        else:
            if self.AWG.run_state() == 'Running':
                self.AWG.stop()
                print(self.AWG.run_state())
            elif self.AWG.run_state() == 'Waiting for trigger':
                print(self.AWG.run_state())
            else:  
                self.AWG.play()
                print(self.AWG.run_state())
            
            self.AWG.stop();


    def runChan(self,outputbox,whichbox):
        if whichbox==0:
            if outputbox.isChecked():
                self.AWG.ch1_state(1);
                self.AWG.ch2_state(1);
                self.AWG.ch3_state(1);
                self.AWG.ch4_state(1);
            else:
                self.AWG.ch1_state(0);
                self.AWG.ch2_state(0);
                self.AWG.ch3_state(0);
                self.AWG.ch4_state(0);
        if whichbox==1:
            if outputbox.isChecked():
                self.AWG.ch1_state(1);
            else:
                self.AWG.ch1_state(0);
        if whichbox==2:
            if outputbox.isChecked():
                self.AWG.ch2_state(1);
            else:
                self.AWG.ch2_state(0);
        if whichbox==3:
            if outputbox.isChecked():
                self.AWG.ch3_state(1);
            else:
                self.AWG.ch3_state(0);
        if whichbox==4:
            if outputbox.isChecked():
                self.AWG.ch4_state(1);
            else:
                self.AWG.ch4_state(0);


# not sure were functions below belong 
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
        awgclock = self.gelem.SR
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