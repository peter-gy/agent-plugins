import { h, nextTick, watch } from 'vue'
import DefaultTheme from 'vitepress/theme'
import { inBrowser, type Theme, useData } from 'vitepress'
import { createMermaidRenderer } from 'vitepress-mermaid-renderer'

import 'vitepress-mermaid-renderer/css'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout: () => {
    const { isDark } = useData()
    const configureMermaid = (): void => {
      const dark = isDark.value
      const renderer = createMermaidRenderer({
        flowchart: {
          htmlLabels: false,
          nodeSpacing: 24,
          rankSpacing: 28,
          useMaxWidth: true
        },
        securityLevel: 'strict',
        startOnLoad: false,
        theme: 'base',
        themeVariables: {
          background: dark ? '#0a0a0a' : '#ffffff',
          primaryColor: dark ? '#171717' : '#f7f7f6',
          primaryTextColor: dark ? '#fafafa' : '#171717',
          primaryBorderColor: dark ? '#525252' : '#a3a3a3',
          secondaryColor: dark ? '#0a0a0a' : '#ffffff',
          secondaryTextColor: dark ? '#e5e5e5' : '#2d2d2d',
          secondaryBorderColor: dark ? '#404040' : '#d4d4d4',
          lineColor: dark ? '#a3a3a3' : '#737373',
          tertiaryColor: dark ? '#262626' : '#eeeeec',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        }
      })
      renderer.setToolbar({
        downloadFormat: 'svg',
        fullscreenMode: 'dialog',
        showLanguageLabel: false,
        desktop: {
          copyCode: 'enabled',
          resetView: 'enabled',
          toggleFullscreen: 'enabled',
          zoomIn: 'enabled',
          zoomLevel: 'enabled',
          zoomOut: 'enabled'
        },
        mobile: {
          copyCode: 'disabled',
          resetView: 'disabled',
          toggleFullscreen: 'disabled',
          zoomIn: 'disabled',
          zoomLevel: 'disabled',
          zoomOut: 'disabled'
        }
      })
    }

    if (inBrowser) {
      void nextTick(configureMermaid)
      watch(isDark, configureMermaid)
    }

    return h(DefaultTheme.Layout)
  }
} satisfies Theme
