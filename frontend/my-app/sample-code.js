// Welcome to Opsis Code Editor!
// This is a sample JavaScript file

// Function to greet
function greet(name) {
  return `Hello, ${name}! Welcome to Opsis Code Editor.`;
}

// Calculate factorial
function factorial(n) {
  if (n <= 1) return 1;
  return n * factorial(n - 1);
}

// Main execution
console.log(greet("Developer"));
console.log("=".repeat(50));

// Test factorial
for (let i = 1; i <= 5; i++) {
  console.log(`Factorial of ${i} = ${factorial(i)}`);
}

console.log("=".repeat(50));

// Array operations
const numbers = [1, 2, 3, 4, 5];
const squared = numbers.map(n => n * n);
console.log("Original:", numbers);
console.log("Squared:", squared);

// Object example
const editor = {
  name: "Opsis Code Editor",
  version: "1.0.0",
  features: ["Syntax Highlighting", "Code Execution", "File Management"],
  supportedLanguages: ["JavaScript", "Python", "Java", "TypeScript", "HTML", "CSS"]
};

console.log("\nEditor Info:");
console.log(JSON.stringify(editor, null, 2));
