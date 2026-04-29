const fs = require('fs');

// Read the DashboardPage.tsx file
const filePath = 'd:/blackhole projects/blackhole-infevers trade/Multi-Asset Trading Dashboard/trading-dashboard/src/pages/DashboardPage.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// The issue is that there's an extra closing brace that terminates the main try block prematurely
// The main try block starts at line 229 and should end at line 523 with its catch block
// But there's an extra } around line 509 that's causing the syntax error

// Find and fix the problematic area where there are three closing braces in a row
// We need to remove one of the extra closing braces that's not needed
const fixedContent = content.replace(
  /(\s*setPreviousPortfolioValue\(totalValue\);\s*\}\s*else\s*\{[\s\S]*?setPreviousPortfolioValue\(totalValue\);\s*\}\s*\}\s*\})\s*\n\s*\/\/ If we reach here/g,
  `$1\n      \n      // If we reach here`
);

// Write the corrected content back to the file
fs.writeFileSync(filePath, fixedContent, 'utf8');
console.log('Fixed the main try block structure in DashboardPage.tsx');