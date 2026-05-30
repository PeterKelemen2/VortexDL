// utils/favicon.js
import { createApp, defineComponent, h } from 'vue'

export async function setLucideFavicon(lucideIcon, { color = 'white', size = 32 } = {}) {
  const wrapper = defineComponent({
    render: () => h(lucideIcon, { size, color, strokeWidth: 2 })
  })

  const app = createApp(wrapper)
  const container = document.createElement('div')
  app.mount(container)

  const svgEl = container.querySelector('svg')
  if (!svgEl) return

  svgEl.setAttribute('width', size)
  svgEl.setAttribute('height', size)

  const svgString = svgEl.outerHTML
  app.unmount()

  const blob = new Blob([svgString], { type: 'image/svg+xml' })
  const href = URL.createObjectURL(blob)

  let link = document.querySelector("link[rel~='icon']")
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = href
}