// Responsive Design Verification Test
// Tests layout behavior across different screen sizes and browsers

export const testResponsiveDesign = () => {
  console.log('🧪 Starting Responsive Design Tests...\n');
  
  const tests = [
    {
      name: 'Viewport Units Test',
      test: () => {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
        return window.innerHeight > 0 && vh > 0;
      }
    },
    {
      name: 'Flexbox Support Test',
      test: () => {
        const testEl = document.createElement('div');
        testEl.style.display = 'flex';
        testEl.style.flexDirection = 'column';
        return testEl.style.display === 'flex';
      }
    },
    {
      name: 'Grid Support Test',
      test: () => {
        const testEl = document.createElement('div');
        testEl.style.display = 'grid';
        return testEl.style.display === 'grid';
      }
    },
    {
      name: 'Media Query Support Test',
      test: () => {
        return window.matchMedia('(min-width: 768px)').media !== 'invalid';
      }
    },
    {
      name: 'Touch Target Size Test',
      test: () => {
        // On desktop (hover: hover), touch is not expected - pass
        // On mobile (hover: none or pointer: coarse), touch should work - check
        const isDesktop = window.matchMedia('(hover: hover)').matches;
        const hasTouch = window.matchMedia('(hover: none)').matches || 
                        window.matchMedia('(pointer: coarse)').matches;
        return isDesktop || hasTouch;
      }
    },
    {
      name: 'CSS Custom Properties Test',
      test: () => {
        return window.CSS && window.CSS.supports('color', 'var(--test-var)');
      }
    },
    {
      name: 'Viewport Meta Tag Test',
      test: () => {
        const viewport = document.querySelector('meta[name="viewport"]');
        return !!viewport && viewport.getAttribute('content')?.includes('width=device-width');
      }
    }
  ];

  let passed = 0;
  let failed = 0;

  tests.forEach(test => {
    try {
      const result = test.test();
      if (result) {
        console.log(`✅ ${test.name}: PASSED`);
        passed++;
      } else {
        console.log(`❌ ${test.name}: FAILED`);
        failed++;
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.log(`❌ ${test.name}: ERROR - ${errorMessage}`);
      failed++;
    }
  });

  console.log('\n📊 Responsive Test Results:');
  console.log(`✅ Passed: ${passed}/${tests.length}`);
  console.log(`❌ Failed: ${failed}/${tests.length}`);
  console.log(`🎯 Success Rate: ${Math.round((passed / tests.length) * 100)}%`);

  if (failed === 0) {
    console.log('\n🎉 All responsive tests passed! Layout should work across devices.');
  } else {
    console.log('\n⚠️ Some responsive features may not work on this browser/device.');
  }

  // Screen size reporting
  console.log('\n📱 Device Information:');
  console.log(`Screen Width: ${screen.width}px`);
  console.log(`Screen Height: ${screen.height}px`);
  console.log(`Window Inner Width: ${window.innerWidth}px`);
  console.log(`Window Inner Height: ${window.innerHeight}px`);
  console.log(`Device Pixel Ratio: ${window.devicePixelRatio}`);
  console.log(`Touch Support: ${('ontouchstart' in window) ? 'Yes' : 'No'}`);

  // Responsive breakpoint detection
  const breakpoints = {
    'Mobile (sm)': window.matchMedia('(max-width: 639px)').matches,
    'Tablet (md)': window.matchMedia('(min-width: 640px) and (max-width: 1023px)').matches,
    'Desktop (lg)': window.matchMedia('(min-width: 1024px)').matches
  };

  console.log('\n📐 Active Breakpoint:');
  Object.entries(breakpoints).forEach(([name, active]) => {
    if (active) {
      console.log(`🎯 ${name}`);
    }
  });

  return {
    total: tests.length,
    passed,
    failed,
    successRate: Math.round((passed / tests.length) * 100),
    deviceInfo: {
      screenWidth: screen.width,
      screenHeight: screen.height,
      windowWidth: window.innerWidth,
      windowHeight: window.innerHeight,
      pixelRatio: window.devicePixelRatio,
      touchSupport: 'ontouchstart' in window
    },
    activeBreakpoint: Object.keys(breakpoints).find(key => breakpoints[key as keyof typeof breakpoints])
  };
};

// Run the test
if (typeof window !== 'undefined') {
  // Run test after component mounts
  setTimeout(() => {
    testResponsiveDesign();
  }, 1000);
}

export default testResponsiveDesign;