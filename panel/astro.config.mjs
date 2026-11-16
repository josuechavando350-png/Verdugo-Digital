import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import starlight from '@astrojs/starlight';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  integrations: [react(), starlight({ pagefind: false, disable404Route: true, title: 'Guía de Verdugo', defaultLocale: 'es', locales: { es: { label: 'Español', lang: 'es' } }, sidebar: [{ label: 'Operación local', link: '/es/operacion/' }] })],
  vite: { plugins: [tailwindcss()] },
  output: 'static',
});
