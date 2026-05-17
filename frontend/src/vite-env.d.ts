/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// 全局 Window 扩展
declare global {
  interface Window {
    ELEMENTS_DEBUG?: any
    debugTreeData?: any
  }

  interface MonacoEnvironment {
    getWorker: (moduleId: string, label: string) => Worker
  }
}
