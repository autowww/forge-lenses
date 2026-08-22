import type { FeatureShowcaseItem } from './types'

/** Example copy + Unsplash URLs — swap `src` for `/your-image.jpg` in `public/` or any CDN. */
export const exampleFeatureShowcaseItems: FeatureShowcaseItem[] = [
  {
    id: 'unified',
    heading: 'One workspace for every repo',
    summary: 'Scan once, browse projects, sites, and roadmaps without switching tools.',
    description: 'Workspace state stays in sync with your filesystem and git metadata.',
    backgroundImage: {
      src: 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=80',
      alt: '',
    },
    mainImage: {
      src: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1000&q=80',
      alt: 'Analytics dashboard on a laptop',
    },
    cta: { label: 'Explore projects', href: '/studio/projects' },
  },
  {
    id: 'charts',
    heading: 'Charts that stay honest',
    summary: 'WBS, timelines, and overview charts generated from the same truth as your boards.',
    description: 'Resize, filter, and drill down without exporting to a spreadsheet.',
    backgroundImage: {
      src: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1400&q=80',
      alt: '',
    },
    mainImage: {
      src: 'https://images.unsplash.com/photo-1543286386-713bdd548da4?auto=format&fit=crop&w=1000&q=80',
      alt: 'Colorful data visualization',
    },
    cta: { label: 'Open charts', href: '/studio/overview/charts' },
  },
  {
    id: 'websites',
    heading: 'Static sites at a glance',
    summary: 'See Firebase-ready sites, page counts, and jump into browse mode fast.',
    backgroundImage: {
      src: 'https://images.unsplash.com/photo-1504639725590-34dda098e8c3?auto=format&fit=crop&w=1400&q=80',
      alt: '',
    },
    mainImage: {
      src: 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1000&q=80',
      alt: 'Laptop showing code editor',
    },
    cta: { label: 'Browse websites', href: '/studio/websites' },
  },
  {
    id: 'boards',
    heading: 'Boards for real work',
    summary: 'Capture stickers, notes, and next steps where your team already looks.',
    backgroundImage: {
      src: 'https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=1400&q=80',
      alt: '',
    },
    mainImage: {
      src: 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1000&q=80',
      alt: 'Team collaborating at a whiteboard',
    },
    cta: { label: 'View boards', href: '/studio/board' },
  },
  {
    id: 'search',
    heading: 'Search that respects your tree',
    summary: 'Ripgrep-backed search across the workspace with sane defaults.',
    backgroundImage: {
      src: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1400&q=80',
      alt: '',
    },
    mainImage: {
      src: 'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1000&q=80',
      alt: 'Developer typing on keyboard',
    },
    cta: { label: 'Try search', href: '/studio/search' },
  },
]
