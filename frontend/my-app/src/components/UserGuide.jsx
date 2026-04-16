import React from 'react';
import { Joyride, STATUS } from 'react-joyride';

const UserGuide = ({ run, setRun, startIndex = 0, appTheme = 'tokyo-night' }) => {
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
      placement: 'center'
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

  const activeSteps = startIndex > 0 ? steps.slice(startIndex) : steps;

  const handleJoyrideCallback = (data) => {
    const { status, action } = data;
    const finishedStatuses = [STATUS.FINISHED, STATUS.SKIPPED];
    
    if (finishedStatuses.includes(status) || action === 'close') {
      setRun(false);
    }
  };

  const getThemeStyles = () => {
    switch(appTheme) {
      case 'tokyo-night':
        return { backgroundColor: '#1a1b26', textColor: '#a9b1d6', primaryColor: '#7aa2f7', arrowColor: '#1a1b26', overlayColor: 'rgba(0, 0, 0, 0.6)' };
      case 'doodle-light':
        return { backgroundColor: '#ffffff', textColor: '#333333', primaryColor: '#ffb86c', arrowColor: '#ffffff', overlayColor: 'rgba(0, 0, 0, 0.4)' };
      case 'doodle-dark':
        return { backgroundColor: '#282a36', textColor: '#f8f8f2', primaryColor: '#bd93f9', arrowColor: '#282a36', overlayColor: 'rgba(0, 0, 0, 0.7)' };
      case 'doodle-white':
        return { backgroundColor: '#fdfdfd', textColor: '#222222', primaryColor: '#6c757d', arrowColor: '#fdfdfd', overlayColor: 'rgba(255, 255, 255, 0.6)' };
      default:
        return { backgroundColor: '#fff', textColor: '#222', primaryColor: '#6da9f8', arrowColor: '#fff', overlayColor: 'rgba(0, 0, 0, 0.5)' };
    }
  };

  return (
    <Joyride
      callback={handleJoyrideCallback}
      continuous={true}
      run={run}
      showProgress={true}
      showSkipButton={true}
      steps={activeSteps}
      styles={{
        options: getThemeStyles()
      }}
      locale={{
        last: 'Finish',
        skip: 'Skip Tour'
      }}
    />
  );
};

export default UserGuide;
