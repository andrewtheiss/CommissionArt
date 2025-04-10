/// <reference types="vite/client" />

interface Window {
  ethereum?: any;
}

// Add JSON module declaration for TypeScript
declare module "*.json" {
  const value: any;
  export default value;
}
