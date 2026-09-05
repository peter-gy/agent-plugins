<script setup lang="ts">
// Icon paths come from Lucide under the ISC license, matching the exported
// core model diagram under public/brand.
const icons = {
  folderTree: [
    'M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z',
    'M20 21a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-2.9a1 1 0 0 1-.88-.55l-.42-.85a1 1 0 0 0-.92-.6H13a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z',
    'M3 5a2 2 0 0 0 2 2h3',
    'M3 3v13a2 2 0 0 0 2 2h3'
  ],
  package: [
    'M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z',
    'M12 22V12',
    'M3.29 7 12 12 20.71 7',
    'm7.5 4.27 9 5.15'
  ],
  hardDriveDownload: [
    'M12 2v8',
    'm16 6-4 4-4-4',
    'M4 14h16a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-4a2 2 0 0 1 2-2z',
    'M6 18h.01',
    'M10 18h.01'
  ],
  scanSearch: [
    'M3 7V5a2 2 0 0 1 2-2h2',
    'M17 3h2a2 2 0 0 1 2 2v2',
    'M21 17v2a2 2 0 0 1-2 2h-2',
    'M7 21H5a2 2 0 0 1-2-2v-2',
    'M15 12a3 3 0 1 1-6 0a3 3 0 1 1 6 0',
    'm16 16-1.9-1.9'
  ],
  braces: [
    'M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1',
    'M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1'
  ],
  plug: [
    'M12 22v-5',
    'M15 8V2',
    'M17 8a1 1 0 0 1 1 1v4a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1z',
    'M9 8V2'
  ],
  chevron: ['m9 18 6-6-6-6']
} as const

type IconName = keyof typeof icons

interface Stage {
  title: string
  mechanism: string
  icon: IconName
  listing: string
}

const stages: Stage[] = [
  {
    title: 'Author',
    mechanism: '[tool.agent-plugins]',
    icon: 'folderTree',
    listing: [
      'my-project/',
      '├─ plugin.json',
      '├─ skills/',
      '└─ packages/python/',
      '   └─ src/my_project/'
    ].join('\n')
  },
  {
    title: 'Build',
    mechanism: 'uv build',
    icon: 'package',
    listing: 'my_project-0.1.0-py3-none-any.whl'
  },
  {
    title: 'Install',
    mechanism: 'pip install dist/*.whl',
    icon: 'hardDriveDownload',
    listing: [
      'site-packages/',
      '├─ my_project/',
      '├─ my_project-0.1.0.agent-plugin/',
      '└─ my_project-0.1.0.dist-info/',
      '   └─ agent_plugins.json'
    ].join('\n')
  },
  {
    title: 'Inspect',
    mechanism: 'import agent_plugins as ap',
    icon: 'scanSearch',
    listing: [
      'ap.locate("my-project")',
      '├─ .manifest',
      '├─ .skills',
      '├─ .mcp',
      '└─ .path'
    ].join('\n')
  }
]
</script>

<template>
  <section class="core-model" aria-labelledby="core-model-title">
    <h2 id="core-model-title" class="title">How it works</h2>
    <p class="lead">
      One Python project carries the library and its Agent Plugin. Building it
      produces one wheel, installing that wheel places both in
      <code>site-packages</code>, and <code>agent_plugins.locate()</code> returns
      the plugin for the installed library version.
    </p>

    <ol class="flow">
      <template v-for="(stage, index) in stages" :key="stage.title">
        <li v-if="index > 0" class="connector" aria-hidden="true">
          <span class="line" />
          <svg class="icon chevron" viewBox="0 0 24 24">
            <path v-for="d in icons.chevron" :key="d" :d="d" />
          </svg>
        </li>
        <li class="stage">
          <h3 class="stage-title">
            <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path v-for="d in icons[stage.icon]" :key="d" :d="d" />
            </svg>
            {{ stage.title }}
          </h3>
          <p class="mechanism">{{ stage.mechanism }}</p>
          <div class="card">
            <pre class="listing">{{ stage.listing }}</pre>
            <p v-if="stage.title === 'Build'" class="parts">
              <span class="part">
                <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path v-for="d in icons.braces" :key="d" :d="d" />
                </svg>
                library
              </span>
              <span class="part">
                <svg class="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path v-for="d in icons.plug" :key="d" :d="d" />
                </svg>
                Agent Plugin
              </span>
              <span class="part">one version</span>
            </p>
          </div>
        </li>
      </template>
    </ol>

  </section>
</template>

<style scoped>
.core-model {
  --core-model-mono: 12px;
  max-width: 1216px;
  margin: 64px auto 40px;
  padding: 0 24px;
}

.title {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.lead {
  max-width: 620px;
  margin: 12px 0 40px;
  color: var(--vp-c-text-2);
  font-size: 16px;
  line-height: 1.6;
}

.lead code {
  padding: 2px 5px;
  border-radius: 4px;
  background: var(--vp-c-default-soft);
  font-family: var(--vp-font-family-mono);
  font-size: 0.9em;
}

.flow {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  max-width: 340px;
  margin: 0 auto;
  padding: 0;
  list-style: none;
}

.stage {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stage-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  color: var(--vp-c-text-1);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 20px;
}

.stage-title .icon {
  width: 18px;
  height: 18px;
}

.mechanism {
  margin: 8px 0 12px;
  color: var(--vp-c-text-3);
  font-family: var(--vp-font-family-mono);
  font-size: 11.5px;
  line-height: 16px;
  white-space: nowrap;
}

.card {
  padding: 10px 14px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
}

.listing {
  margin: 0;
  overflow-x: auto;
  color: var(--vp-c-text-1);
  font-family: var(--vp-font-family-mono);
  font-size: var(--core-model-mono);
  line-height: 1.5;
  white-space: pre;
}

.parts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin: 6px 0 0;
  color: var(--vp-c-text-3);
  font-size: 11.5px;
  line-height: 16px;
}

.part {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.part .icon {
  width: 13px;
  height: 13px;
}

.icon {
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.connector {
  display: flex;
  flex-direction: column;
  align-items: center;
  align-self: center;
  padding: 8px 0;
  color: var(--vp-c-text-3);
}

.connector .line {
  width: 1px;
  height: 12px;
  background: currentColor;
  opacity: 0.5;
}

.connector .chevron {
  width: 14px;
  height: 14px;
  transform: rotate(90deg);
}

@media (min-width: 640px) {
  .core-model {
    padding: 0 48px;
  }
}

@media (min-width: 1024px) {
  .core-model {
    --core-model-mono: 10.5px;
    margin: 80px auto 56px;
    padding: 0 24px;
  }

  .flow {
    flex-direction: row;
    align-items: flex-start;
    justify-content: safe center;
    max-width: none;
    overflow-x: auto;
  }

  .stage {
    flex: none;
  }

  /* Card top = title 20 + gap 8 + mechanism 16 + gap 12; the chevron centers
     on the card's first text line. */
  .connector {
    flex: none;
    flex-direction: row;
    align-self: flex-start;
    margin-top: 68px;
    padding: 0 8px;
  }

  .connector .line {
    width: 12px;
    height: 1px;
  }

  .connector .chevron {
    transform: none;
  }
}

@media (min-width: 1152px) {
  .core-model {
    --core-model-mono: 11px;
    padding: 0 32px;
  }

  .connector {
    padding: 0 10px;
  }

  .connector .line {
    width: 14px;
  }
}

@media (min-width: 1280px) {
  .core-model {
    --core-model-mono: 12px;
  }

  .connector {
    padding: 0 18px;
  }

  .connector .line {
    width: 22px;
  }
}
</style>
