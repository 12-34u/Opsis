import React, { useState, useEffect } from 'react';
import { Joyride, STATUS } from 'react-joyride';

const UserGuide = ({ run, setRun }) => {

  useEffect(() => {
    const isTourSeen = localStorage.getItem('opsis-tour-seen');
    if (!isTourSeen) {
      setRun(true);
    }
  }, [setRun]);

  const steps = [
    {
      target: 'body',
      content: (
        <div>
          <h3>Welcome to Opsis! 🚀</h3>
          <p>Let's take a quick tour to help you get familiar with your new 8085/8086 Assembly environment.</p>
        </div>
      ),
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '.editor-container',
      content: (
        <div>
          <h3>Code Editor 💻</h3>
          <p>This is where you'll write all your assembly code. It features intelligent syntax highlighting tailored for assembly instructions, line numbers, and a minimap to make navigating large programs a breeze.</p>
        </div>
      ),
      disableBeacon: true,
      placement: 'right'
    },
    {
      target: '.op-sidebar',
      content: (
        <div>
          <h3>Registers & Flags 📊</h3>
          <p>
            <strong>Registers</strong> (like A, B, C) are incredibly fast, tiny storage slots directly inside the CPU. They hold data temporarily while instructions execute.
            <br/><br/>
            <strong>Flags</strong> (like Zero, Carry) are 1-bit indicators that show the status or outcome of your last operation. Watch these numbers flip as you step through code!
          </p>
        </div>
      ),
      placement: 'left'
    },
    {
      target: '.assembly-panels',
      content: (
        <div>
          <h3>Execution Panel & Memory 🔍</h3>
          <p>The control center for running code. When you hit run, you can step sequentially through your program here. You'll see memory values changing at specific addresses and any I/O outputs printed step-by-step.</p>
        </div>
      ),
      placement: 'top'
    },
    {
      target: '.file-explorer',
      content: (
        <div>
          <h3>File Explorer 📁</h3>
          <p>Organize your work effortlessly. You can save and open multiple `.asm` files, making it easy to manage larger assembly projects.</p>
        </div>
      ),
      placement: 'right'
    }
  ];

  const handleJoyrideCallback = (data) => {
    const { status } = data;
    const finishedStatuses = [STATUS.FINISHED, STATUS.SKIPPED];
    if (finishedStatuses.includes(status)) {
      setRun(false);
      localStorage.setItem('opsis-tour-seen', 'true');
    }
  };

  return (
    <Joyride
      callback={handleJoyrideCallback}
      continuous
      hideCloseButton={false}
      run={run}
      scrollToFirstStep
      showProgress
      showSkipButton
      steps={steps}
      styles={{
        options: {
          zIndex: 10000,
          primaryColor: '#6da9f8', 
          textColor: '#222',
          backgroundColor: '#fff',
        },
        buttonClose: {
          display: 'none',
        }
      }}
      locale={{
        last: 'Finish',
        skip: 'Skip Tour'
      }}
    />
  );
};

export default UserGuide;
