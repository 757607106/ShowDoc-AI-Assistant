<template>
  <section ref="rootRef" class="showcase" :class="{ 'reduced-motion': reducedMotion }"
    :aria-labelledby="'login-scene-title-' + current">
    <div class="intro">
      <div v-for="(theme, index) in themes" :key="sceneKeys[index]" class="intro-theme"
        :class="{ 'is-active': current === index }" :aria-hidden="current !== index">
        <h1 :id="'login-scene-title-' + index">{{ theme.title }}</h1>
        <p>{{ theme.description }}</p>
      </div>
    </div>
    <div ref="carouselRef" class="carousel" role="region"
      :aria-label="t('platform.loginShowcase.carouselLabel')"
      @focusin="handleFocusIn" @focusout="handleFocusOut">
      <div class="stage" @pointerenter="handlePointerEnter" @pointerleave="hovered = false">
      <svg id="login-illustration" class="illustration" viewBox="0 0 760 430" role="img" aria-labelledby="login-art-title login-art-description">
        <title id="login-art-title">{{ activeTheme.title }}</title>
        <desc id="login-art-description">{{ activeTheme.summary }}</desc>
        <defs>
          <linearGradient id="login-paper-face" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="#f6fcff" />
            <stop offset="1" stop-color="#c5e3f2" />
          </linearGradient>
          <linearGradient id="login-blue-face" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="#72b6d9" />
            <stop offset="1" stop-color="#326986" />
          </linearGradient>
          <linearGradient id="login-glass-face" x1="0" y1="0" x2="1" y2="1">
            <stop stop-color="#e1f5ff" stop-opacity=".28" />
            <stop offset="1" stop-color="#a5d8f0" stop-opacity=".08" />
          </linearGradient>
          <filter id="login-soft-object-shadow" x="-30%" y="-20%" width="170%" height="170%">
            <feDropShadow dx="0" dy="12" stdDeviation="12" flood-color="#0b2035" flood-opacity=".16" />
          </filter>
          <symbol id="login-document-shape" viewBox="0 0 76 94">
            <path d="M9 3h42l17 17v66a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8a5 5 0 0 1 5-5Z" fill="url(#login-paper-face)" stroke="#a2cde2" stroke-width="1.3" />
            <path d="M51 3v13a4 4 0 0 0 4 4h13" fill="#b5d8eb" stroke="#a2cde2" stroke-width="1.1" />
            <path d="M17 32h26M17 44h37M17 54h37M17 64h29" stroke="#7baac4" stroke-width="2" stroke-linecap="round" />
          </symbol>
          <symbol id="login-web-shape" viewBox="0 0 110 80">
            <rect x="4" y="4" width="102" height="72" rx="7" fill="url(#login-paper-face)" stroke="#9ac6de" stroke-width="1.4" />
            <path d="M4 22h102" stroke="#b0d4e6" />
            <circle cx="15" cy="13" r="2" fill="#7ba8c2" />
            <circle cx="23" cy="13" r="2" fill="#a0c8dd" />
            <rect x="15" y="33" width="24" height="30" rx="3" fill="#a7d1e6" />
            <path d="M49 36h40M49 47h34M49 58h25" stroke="#7baac4" stroke-width="2" stroke-linecap="round" />
          </symbol>
          <symbol id="login-folder-shape" viewBox="0 0 145 112">
            <path d="M7 21a7 7 0 0 1 7-7h39l13 13h66a7 7 0 0 1 7 7v65H7Z" fill="#82bbd8" stroke="#bbdfef" />
            <path d="M14 37h118v59H14Z" fill="#d8edf7" />
            <path d="M5 49a6 6 0 0 1 6-6h121a6 6 0 0 1 6 6l-9 51H14Z" fill="url(#login-paper-face)" stroke="#a6cfe3" stroke-width="1.4" />
            <path d="M26 63h37" stroke="#89b6ce" stroke-width="3" stroke-linecap="round" />
          </symbol>
        </defs>
        <g class="art-scene" :class="{ 'is-active': current === 0 }" data-scene="0" :aria-hidden="current !== 0">
          <path class="flow-route" d="M157 219 C197 219 207 211 234 211" data-start="350" data-duration="1000" />
          <circle class="traveler" r="2.7" />
          <path class="flow-route" d="M418 208 C482 208 491 232 559 232" data-start="1800" data-duration="1250" />
          <circle class="traveler" r="2.7" />
          <g transform="translate(58 167)">
            <path d="M15 6h64a12 12 0 0 1 12 12v43a12 12 0 0 1-12 12H47L28 88V73H15A12 12 0 0 1 3 61V18A12 12 0 0 1 15 6Z" fill="url(#login-glass-face)" stroke="#d4effc" stroke-width="1.5" />
            <circle cx="28" cy="40" r="3" fill="#e8f8ff" />
            <circle cx="47" cy="40" r="3" fill="#e8f8ff" />
            <circle cx="66" cy="40" r="3" fill="#e8f8ff" />
          </g>
          <text class="art-label" x="104" y="282" text-anchor="middle">{{ t('platform.loginShowcase.labels.query') }}</text>
          <g class="primary">
            <circle cx="348" cy="210" r="115" fill="url(#login-glass-face)" stroke="#bedff0" stroke-width="1.3" />
            <g transform="translate(280 116) scale(1.78)">
              <g>
                <use href="#login-document-shape" width="76" height="94" />
              </g>
            </g>
            <g class="reaction source-highlight" data-at="1400">
              <rect x="310" y="199" width="84" height="17" rx="3" fill="#8fcde9" opacity=".68" />
              <path d="M314 207h69" stroke="#326986" stroke-width="2" />
            </g>
            <circle cx="348" cy="210" r="108" fill="none" stroke="#e4f5fd" stroke-width="9" />
            <path d="m426 290 55 55" stroke="#7cafca" stroke-width="23" stroke-linecap="round" />
            <path d="m426 286 55 55" stroke="#d5edf8" stroke-width="14" stroke-linecap="round" />
          </g>
          <text class="art-label" x="344" y="377" text-anchor="middle">{{ t('platform.loginShowcase.labels.sourceHit') }}</text>
          <g class="reaction answer-result" data-at="3050" data-motion="settle">
            <path d="M576 193h49l14 14v52a5 5 0 0 1-5 5h-58a5 5 0 0 1-5-5v-61a5 5 0 0 1 5-5Z" fill="url(#login-paper-face)" stroke="#badcee" stroke-width="1.3" />
            <text x="603" y="243" text-anchor="middle" font-size="31" fill="#326986" font-weight="500">1</text>
            <text class="art-label light" x="605" y="301" text-anchor="middle">{{ t('platform.loginShowcase.labels.citedAnswer') }}</text>
            <path d="m656 218 5 5 11-13" stroke="#e2f5ff" stroke-width="2.3" fill="none" stroke-linecap="round" stroke-linejoin="round" />
          </g>
        </g>
        <g class="art-scene" :class="{ 'is-active': current === 1 }" data-scene="1" :aria-hidden="current !== 1">
          <path class="flow-route" d="M139 218 C181 218 195 218 223 218" data-start="350" data-duration="1100" />
          <circle class="traveler" r="2.7" />
          <path class="flow-route" d="M242 218 C267 218 257 110 303 110" data-start="1550" data-duration="1000" />
          <circle class="traveler" r="2.7" />
          <path class="flow-route" d="M242 218 C382 218 439 216 523 216" data-start="1550" data-duration="1250" />
          <circle class="traveler" r="2.7" />
          <path class="flow-route" d="M242 218 C276 218 271 331 310 331" data-start="1550" data-duration="1100" />
          <circle class="traveler" r="2.7" />
          <g transform="translate(56 171) scale(0.83)">
            <g>
              <use href="#login-document-shape" width="76" height="94" />
            </g>
          </g>
          <g transform="translate(74 183) scale(0.83)">
            <g>
              <use href="#login-document-shape" width="76" height="94" />
            </g>
          </g>
          <text class="art-label" x="107" y="301" text-anchor="middle">{{ t('platform.loginShowcase.labels.sourceMaterial') }}</text>
          <g transform="translate(224 206)">
            <circle cx="9" cy="12" r="16" fill="#b4dced" stroke="#d7effa" />
            <path d="M4 7h10M4 12h10M4 17h10" stroke="#44778f" stroke-width="1.7" />
          </g>
          <g class="reaction category-product" data-at="2550" data-motion="unfold">
            <use href="#login-folder-shape" x="300" y="45" width="154" height="119" />
            <text class="art-label" x="376" y="192" text-anchor="middle">{{ t('platform.loginShowcase.labels.productKnowledge') }}</text>
            <g class="related-links">
              <path d="M453 101h26m-6 0v-20h20m-20 20v20h20" fill="none" stroke="#b5deef" stroke-width="1.2" />
              <circle cx="499" cy="81" r="4" fill="#c9e8f5" />
              <circle cx="499" cy="121" r="4" fill="#c9e8f5" />
            </g>
          </g>
          <g class="reaction category-delivery" data-at="2800" data-motion="unfold">
            <rect x="544" y="150" width="108" height="135" rx="8" fill="url(#login-paper-face)" stroke="#b1d6e9" stroke-width="1.3" />
            <rect x="571" y="142" width="54" height="17" rx="5" fill="#91bfd8" stroke="#c5e4f3" />
            <g fill="none" stroke="#71a3bf" stroke-width="2">
              <path d="m562 183 4 4 7-9m-11 32 4 4 7-9m-11 32 4 4 7-9" />
              <path d="M584 183h45M584 206h37M584 229h45" />
            </g>
            <text class="art-label light" x="599" y="318" text-anchor="middle">{{ t('platform.loginShowcase.labels.delivery') }}</text>
          </g>
          <g class="reaction category-service" data-at="2650" data-motion="unfold">
            <path d="M328 280h104a8 8 0 0 1 8 8v46a8 8 0 0 1-8 8h-32l-17 14v-14h-55a8 8 0 0 1-8-8v-46a8 8 0 0 1 8-8Z" fill="#a0cde3" stroke="#c3e3f2" />
            <path d="M313 266h104a8 8 0 0 1 8 8v46a8 8 0 0 1-8 8h-60l-17 14v-14h-27a8 8 0 0 1-8-8v-46a8 8 0 0 1 8-8Z" fill="url(#login-paper-face)" stroke="#badced" stroke-width="1.4" />
            <path d="M325 287h65M325 301h47" stroke="#7aa9c2" stroke-width="2.5" stroke-linecap="round" />
            <text class="art-label" x="369" y="383" text-anchor="middle">{{ t('platform.loginShowcase.labels.customerService') }}</text>
          </g>
        </g>
        <g class="art-scene" :class="{ 'is-active': current === 2 }" data-scene="2" :aria-hidden="current !== 2">
          <path class="flow-route" d="M152 111 C253 111 290 170 413 170" data-start="350" data-duration="1250" />
          <circle class="traveler" r="2.7" />
          <path class="flow-route" d="M297 79 C365 79 346 208 414 208" data-start="700" data-duration="1300" />
          <circle class="traveler" r="2.7" />
          <path class="flow-route" d="M172 310 C275 310 301 260 415 260" data-start="1050" data-duration="1300" />
          <circle class="traveler" r="2.7" />
          <g transform="translate(72 63) scale(1)">
            <g>
              <use href="#login-document-shape" width="76" height="94" />
            </g>
          </g>
          <text class="art-label" x="110" y="184" text-anchor="middle">{{ t('platform.loginShowcase.labels.documents') }}</text>
          <use href="#login-web-shape" x="232" y="33" width="112" height="82" />
          <text class="art-label" x="288" y="145" text-anchor="middle">{{ t('platform.loginShowcase.labels.webContent') }}</text>
          <use href="#login-folder-shape" x="67" y="260" width="118" height="91" />
          <text class="art-label" x="125" y="383" text-anchor="middle">{{ t('platform.loginShowcase.labels.existingKnowledge') }}</text>
          <g class="primary" transform="translate(412 108) scale(1.06)">
            <g filter="url(#login-soft-object-shadow)">
              <path d="M10 20a12 12 0 0 1 12-12h181a12 12 0 0 1 12 12v174H10Z" fill="url(#login-glass-face)" stroke="#c7e9f8" stroke-width="1.4" />
              <path d="M22 8h52l13 13h116" stroke="#e5f6ff" stroke-width="2" fill="none" />
              <g transform="translate(32 38) scale(1.05)">
                <g>
                  <use href="#login-document-shape" width="76" height="94" />
                </g>
              </g>
              <g transform="translate(105 25) scale(1.13)">
                <g>
                  <use href="#login-document-shape" width="76" height="94" />
                </g>
              </g>
              <g class="reaction merge-sheet" data-at="2350" data-motion="merge">
                <g transform="translate(70 57) scale(1.1)">
                  <g>
                    <use href="#login-document-shape" width="76" height="94" />
                  </g>
                </g>
              </g>
              <path d="M5 121a8 8 0 0 1 8-8h67l15 13h116a9 9 0 0 1 9 9l-10 66H16Z" fill="url(#login-blue-face)" stroke="#b6dff2" stroke-width="1.5" />
              <path d="M32 146h45M32 158h90" stroke="#c3e7f7" stroke-width="3" stroke-linecap="round" opacity=".8" />
            </g>
          </g>
          <text class="art-label light" x="529" y="369" text-anchor="middle">{{ t('platform.loginShowcase.labels.knowledgeEntry') }}</text>
          <g class="reaction result-feedback" data-at="2850">
            <circle cx="657" cy="305" r="14" fill="#d6effa" />
            <path d="m650 305 5 5 10-12" stroke="#326986" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" />
            <text class="art-label light" x="655" y="342" text-anchor="middle">{{ t('platform.loginShowcase.labels.materialsReceived') }}</text>
          </g>
        </g>
        <g class="art-scene" :class="{ 'is-active': current === 3 }" data-scene="3" :aria-hidden="current !== 3">
          <path class="flow-route" d="M161 217 C218 217 230 217 262 217" data-start="350" data-duration="1150" />
          <circle class="traveler" r="2.7" />
          <path class="flow-route" d="M397 217 C455 217 477 217 520 217" data-start="2100" data-duration="1100" />
          <circle class="traveler" r="2.7" />
          <g transform="translate(69 161) scale(1.12)">
            <g>
              <use href="#login-document-shape" width="76" height="94" />
            </g>
          </g>
          <circle cx="139" cy="175" r="12" fill="#d5effb" stroke="#a0cce1" />
          <path d="M133 175h12m-6-6v12" stroke="#326986" stroke-width="1.7" />
          <text class="art-label" x="115" y="306" text-anchor="middle">{{ t('platform.loginShowcase.labels.contentChange') }}</text>
          <g class="primary">
            <circle cx="330" cy="217" r="67" fill="url(#login-glass-face)" stroke="#d5effa" stroke-width="1.5" />
            <circle cx="330" cy="217" r="54" fill="none" stroke="#b2d8ea" stroke-opacity=".5" />
            <g class="reaction review-check" data-at="1500" data-motion="confirm">
              <path d="m305 215 18 18 34-39" stroke="#e5f6ff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" fill="none" />
            </g>
            <text class="art-label" x="330" y="324" text-anchor="middle">{{ t('platform.loginShowcase.labels.knowledgeReview') }}</text>
          </g>
          <g class="primary" transform="translate(520 130) scale(0.78)">
            <g filter="url(#login-soft-object-shadow)">
              <path d="M10 20a12 12 0 0 1 12-12h181a12 12 0 0 1 12 12v174H10Z" fill="url(#login-glass-face)" stroke="#c7e9f8" stroke-width="1.4" />
              <path d="M22 8h52l13 13h116" stroke="#e5f6ff" stroke-width="2" fill="none" />
              <g transform="translate(32 38) scale(1.05)">
                <g>
                  <use href="#login-document-shape" width="76" height="94" />
                </g>
              </g>
              <g transform="translate(105 25) scale(1.13)">
                <g>
                  <use href="#login-document-shape" width="76" height="94" />
                </g>
              </g>
              <g class="reaction merge-sheet" data-at="3200" data-motion="merge">
                <g transform="translate(70 57) scale(1.1)">
                  <g>
                    <use href="#login-document-shape" width="76" height="94" />
                  </g>
                </g>
              </g>
              <path d="M5 121a8 8 0 0 1 8-8h67l15 13h116a9 9 0 0 1 9 9l-10 66H16Z" fill="url(#login-blue-face)" stroke="#b6dff2" stroke-width="1.5" />
              <path d="M32 146h45M32 158h90" stroke="#c3e7f7" stroke-width="3" stroke-linecap="round" opacity=".8" />
            </g>
          </g>
          <g class="reaction updated-sheet" data-at="3200" data-motion="merge">
            <rect x="607" y="187" width="43" height="16" rx="3" fill="#d2eefb" />
            <path d="M616 195h25" stroke="#326986" stroke-width="2" />
          </g>
          <text class="art-label light" x="608" y="343" text-anchor="middle">{{ t('platform.loginShowcase.labels.knowledgeUpdate') }}</text>
          <g class="reaction result-feedback" data-at="3650">
            <path d="m560 378 5 5 10-12" stroke="#c6e9f8" stroke-width="2" fill="none" />
            <text x="584" y="383" class="feedback-label">{{ t('platform.loginShowcase.labels.updateConfirmed') }}</text>
          </g>
        </g>
      </svg>
      </div>
      <p class="mobile-summary">{{ activeTheme.mobile }}</p>
      <div class="carousel-controls">
        <div class="scene-tabs" role="group" :aria-label="t('platform.loginShowcase.switchLabel')">
          <button v-for="(theme, index) in themes" :key="sceneKeys[index]" class="scene-tab" type="button"
            :data-slide="index" :aria-pressed="current === index" aria-controls="login-illustration"
            @click="selectScene(index)">
            {{ theme.tab }}<span class="tab-progress"></span>
          </button>
        </div>
        <span class="scene-counter">{{ String(current + 1).padStart(2, '0') }} / 04</span>
        <button ref="playbackRef" class="playback" type="button" :aria-label="playbackLabel"
          :aria-pressed="paused" :disabled="reducedMotion" @click="togglePlayback">
          <span :class="paused || reducedMotion ? 'play-symbol' : 'pause-symbol'" aria-hidden="true"></span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{ formActive?: boolean }>(), { formActive: false })
const { t } = useI18n()
const sceneKeys = ['query', 'organization', 'intake', 'review'] as const
const themes = computed(() => sceneKeys.map(key => {
  const prefix = 'platform.loginShowcase.themes.' + key
  return {
    title: t(prefix + '.title'),
    description: t(prefix + '.description'),
    summary: t(prefix + '.summary'),
    mobile: t(prefix + '.mobile'),
    tab: t(prefix + '.tab'),
  }
}))

const cycleDuration = 2000
const transitionDuration = 200
const storySpeed = 0.32
const current = ref(0)
const paused = ref(false)
const reducedMotion = ref(false)
const hovered = ref(false)
const focused = ref(false)
const visible = ref(true)
const explicitlyPlaying = ref(false)
const rootRef = ref<HTMLElement | null>(null)
const carouselRef = ref<HTMLElement | null>(null)
const playbackRef = ref<HTMLButtonElement | null>(null)
const activeTheme = computed(() => themes.value[current.value])
const playbackLabel = computed(() => t('platform.loginShowcase.' + (
  reducedMotion.value ? 'reducedMotion' : paused.value ? 'play' : 'pause'
)))

let cycleId = 0
let animations: Animation[] = []
const outgoingAnimations = new Set<Animation>()
const retirementTimers = new Set<number>()
let routes: SVGPathElement[][] = []
let travelers: SVGCircleElement[][] = []
let keyframes: Keyframe[][][] = []
let scenes: SVGGElement[] = []
let progressElements: HTMLElement[] = []
let mediaQuery: MediaQueryList | null = null
let observer: IntersectionObserver | null = null

function clearCycle(preservePrevious = false) {
  cycleId++
  if (!preservePrevious) {
    outgoingAnimations.forEach(animation => animation.cancel())
    outgoingAnimations.clear()
  }
  const previous = animations
  animations = []
  if (preservePrevious) {
    previous.forEach(animation => {
      animation.pause()
      outgoingAnimations.add(animation)
    })
    // Preserve the outgoing frame until its crossfade is complete.
    const timer = window.setTimeout(() => {
      previous.forEach(animation => {
        animation.cancel()
        outgoingAnimations.delete(animation)
      })
      retirementTimers.delete(timer)
    }, transitionDuration)
    retirementTimers.add(timer)
  } else {
    previous.forEach(animation => animation.cancel())
  }
}

function syncPlayback() {
  const shouldPlay = !paused.value && !reducedMotion.value && !document.hidden &&
    visible.value && !props.formActive &&
    (explicitlyPlaying.value || !(hovered.value || focused.value))

  animations.forEach(animation => {
    if (animation.playState === 'finished') return
    if (shouldPlay) animation.play()
    else animation.pause()
  })
}

function buildCycle(preservePrevious = false) {
  clearCycle(preservePrevious)
  if (reducedMotion.value || !progressElements[current.value]) return

  const identifier = cycleId
  const progress = progressElements[current.value].animate(
    [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }],
    { duration: cycleDuration, fill: 'forwards' },
  )
  animations.push(progress)
  progress.onfinish = () => {
    if (identifier === cycleId) selectScene((current.value + 1) % sceneKeys.length)
  }

  routes[current.value].forEach((path, index) => {
    animations.push(travelers[current.value][index].animate(keyframes[current.value][index], {
      duration: Math.round(Number(path.dataset.duration) * storySpeed),
      delay: Math.round(Number(path.dataset.start) * storySpeed),
      fill: 'both',
    }))
  })
  scenes[current.value].querySelectorAll<SVGGElement>('.reaction').forEach(element => {
    const motion = element.dataset.motion
    const start: Keyframe = { opacity: 0.46 }
    const end: Keyframe = { opacity: 1 }
    if (motion === 'merge') {
      start.transform = 'translate(-12px,-4px)'
      end.transform = 'translate(0,0)'
    }
    if (motion === 'unfold') {
      start.transform = 'translate(-6px,0)'
      end.transform = 'translate(0,0)'
    }
    if (motion === 'settle') {
      start.transform = 'translate(0,4px)'
      end.transform = 'translate(0,0)'
    }
    animations.push(element.animate([start, end], {
      duration: motion ? 220 : 150,
      delay: Math.round(Number(element.dataset.at) * storySpeed),
      fill: 'both',
      easing: 'ease-out',
    }))
  })
  syncPlayback()
}

function selectScene(index: number) {
  const preservePrevious = index !== current.value && !reducedMotion.value
  current.value = index
  buildCycle(preservePrevious)
}

function togglePlayback() {
  paused.value = !paused.value
  explicitlyPlaying.value = !paused.value
}

function handlePointerEnter() {
  hovered.value = true
  explicitlyPlaying.value = false
}

function handleFocusIn(event: FocusEvent) {
  if (event.target === playbackRef.value) return
  focused.value = true
  explicitlyPlaying.value = false
}

function handleFocusOut(event: FocusEvent) {
  const nextTarget = event.relatedTarget
  focused.value = nextTarget instanceof Node && !!carouselRef.value?.contains(nextTarget) &&
    nextTarget !== playbackRef.value
}

function handleMotionPreference(event: MediaQueryListEvent) {
  reducedMotion.value = event.matches
  buildCycle()
}

watch([paused, hovered, focused, visible, explicitlyPlaying, () => props.formActive], syncPlayback)

function initializeMotion() {
  const root = rootRef.value
  if (!root || !carouselRef.value) return
  scenes = [...root.querySelectorAll<SVGGElement>('.art-scene')]
  progressElements = [...root.querySelectorAll<HTMLElement>('.tab-progress')]
  routes = scenes.map(scene => [...scene.querySelectorAll<SVGPathElement>('.flow-route')])
  travelers = scenes.map(scene => [...scene.querySelectorAll<SVGCircleElement>('.traveler')])
  // Fixed SVG coordinates let us sample once and animate without frame-by-frame measurements.
  keyframes = routes.map(paths => paths.map(path => {
    const length = path.getTotalLength()
    return Array.from({ length: 81 }, (_, index) => {
      const point = path.getPointAtLength(length * index / 80)
      return {
        transform: 'translate(' + point.x + 'px,' + point.y + 'px)',
        opacity: Math.min(1, index / 10, (80 - index) / 14),
      }
    })
  }))
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion.value = mediaQuery.matches
  mediaQuery.addEventListener('change', handleMotionPreference)
  document.addEventListener('visibilitychange', syncPlayback)
  observer = new IntersectionObserver(entries => {
    visible.value = entries[0].isIntersecting
  }, { threshold: 0.2 })
  observer.observe(carouselRef.value)
  buildCycle()
}

onMounted(initializeMotion)
onBeforeUnmount(() => {
  clearCycle()
  retirementTimers.forEach(timer => window.clearTimeout(timer))
  retirementTimers.clear()
  observer?.disconnect()
  mediaQuery?.removeEventListener('change', handleMotionPreference)
  document.removeEventListener('visibilitychange', syncPlayback)
})
</script>

<style scoped>
.showcase { min-width: 0; }
.showcase h1, .showcase p { margin: 0; }
.intro { margin-bottom: 28px; color: #fff; }

.intro p { margin-top: 8px; font-size: 15px; line-height: 1.6; }
.carousel { min-width: 0; }

.intro h1 { font-size: 29px; font-weight: 500; line-height: 1.4; margin: 0; text-wrap: balance; }
.intro p { color: #e1f1fa; }
.showcase button { font-family: inherit; cursor: pointer; }
.showcase button:disabled { cursor: default; }
.showcase button:focus-visible { outline: 3px solid #9fd1ee; outline-offset: 4px; }
.showcase { max-width: 790px; width: 100%; }
.stage { width: 100%; aspect-ratio: 760 / 430; min-width: 0; position: relative; }
.illustration { display: block; width: 100%; height: 100%; overflow: visible; }
.art-scene {
  opacity: 0;
  visibility: hidden;
  transition: opacity 200ms ease-in-out, visibility 0s linear 200ms;
}
.art-scene.is-active {
  opacity: 1;
  visibility: visible;
  transition-delay: 0s;
}
.intro { display: grid; }
.intro-theme {
  grid-area: 1 / 1;
  opacity: 0;
  visibility: hidden;
  transform: translateY(2px);
  transition: opacity 200ms ease-in-out, transform 200ms ease-out, visibility 0s linear 200ms;
}
.intro-theme.is-active {
  opacity: 1;
  visibility: visible;
  transform: none;
  transition-delay: 0s;
}
.art-label { font-size: 17px; font-weight: 500; fill: #0b2035; }
.art-label.light { fill: #f1f9ff; }
.feedback-label { font-size: 14px; fill: #e9f7ff; }
.flow-route { fill: none; stroke: #c4e7f7; stroke-opacity: .48; stroke-width: 1.15; vector-effect: non-scaling-stroke; }
.traveler { fill: #f3fcff; opacity: 0; }
.reaction { opacity: .46; }
.carousel-controls { display: flex; align-items: center; gap: 18px; margin-top: 17px; }
.scene-tabs { display: flex; flex: 1; gap: 17px; min-width: 0; }
.scene-tab { position: relative; padding: 10px 0 13px; flex: 1; min-height: 42px; border: 0; border-bottom: 1px solid rgba(220,244,255,.26); background: transparent; color: #e5f3fc; font-size: 13px; text-align: left; }
.scene-tab { transition: color 140ms ease-out, border-color 140ms ease-out; }
.scene-tab[aria-pressed="true"] { border-bottom-color: #e2f5ff; color: #fff; font-weight: 500; }
.tab-progress { position: absolute; inset: auto 0 0; height: 2px; background: #e1f5ff; transform: scaleX(0); transform-origin: left; }
.scene-counter { color: #e5f3fc; font-size: 11px; white-space: nowrap; font-variant-numeric: tabular-nums; }
.playback { background: transparent; border: 1px solid rgba(223,245,255,.4); border-radius: 6px; color: #f3fbff; width: 29px; height: 29px; flex-shrink: 0; display: grid; place-items: center; }
.playback { transition: background-color 140ms ease-out, transform 120ms ease-out; }
.playback:hover { background-color: rgba(220,243,255,.12); }
.playback:active { transform: scale(.95); }
.pause-symbol { display: flex; gap: 3px; }
.pause-symbol::before,.pause-symbol::after { content: ""; height: 10px; width: 2px; background: currentColor; }
.play-symbol { width: 0; height: 0; border-top: 5px solid transparent; border-bottom: 5px solid transparent; border-left: 7px solid currentColor; margin-left: 2px; }
.mobile-summary { display: none; }
.reduced-motion .reaction { opacity: 1; }

@media (max-width: 520px) {
  .intro { margin-bottom: 14px; }
  .intro h1 { font-size: 23px; }
  .intro p { font-size: 13px; }
  .illustration .art-label { font-size: 30px; }
  .illustration .feedback-label { display: none; }
  .mobile-summary { display: block; color: #f1f9ff; font-size: 12px; line-height: 1.7; margin-top: 11px; }
  .carousel-controls { gap: 9px; margin-top: 13px; }
  .scene-tabs { gap: 10px; }
  .scene-tab { font-size: 11px; padding-bottom: 10px; }
  .scene-counter { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .art-scene, .intro-theme, .scene-tab, .playback { transition: none; }
  .intro-theme { transform: none; }
  .traveler { display: none; }
  .reaction { opacity: 1; }
}
</style>
