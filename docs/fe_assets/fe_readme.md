# Carrot Game SDK

This is a web game engine powered by Svelte 5, PixiJS 8 and TurboRepo.

## Dependencies

Besides basic web skills (html, css and javascript), here it shows a list of npm dependencies of this repo. It would be great to start with understanding them before kicking off [Get Started](#getStarted).

- pixijs: https://www.npmjs.com/package/pixi.js and [more...](https://pixijs.download/release/docs/index.html)
- svelte: https://www.npmjs.com/package/svelte and [more...](https://svelte.dev/docs/svelte/overview)
- turborepo: https://www.npmjs.com/package/turbo and [more...](https://turbo.build/repo/docs)
- pixi-svelte: https://www.npmjs.com/package/pixi-svelte and [more...](https://github.com/qk0106/pixi-svelte-storybook)
  - This is an in-house package. It combines pixi and svelte together and uses pixijs in a declarative way.
- sveltekit: https://www.npmjs.com/package/@sveltejs/kit and [more...](https://svelte.dev/docs/kit/introduction)
- storybook: https://www.npmjs.com/package/storybook and [more...](https://storybook.js.org/tutorials/intro-to-storybook/svelte/en/get-started/)
- xstate: https://www.npmjs.com/package/xstate and [more...](https://stately.ai/docs/)
- typescript: https://www.npmjs.com/package/typescript and [more...](https://www.typescriptlang.org/docs/)
- pnpm: https://www.npmjs.com/package/pnpm and [more...](https://pnpm.io/installation)

## <a name="getStarted"></a>Get started

Here is a complete tutorial to start our sample games in the storybook. Please ignore those steps that you already know or done.

- It is preferred to use VS Code as IDE. [download](https://code.visualstudio.com/download)
- Install node with version 18.18.0. [download](https://nodejs.org/en/download)

```
# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash

# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"

# Download and install Node.js:
nvm install 18.18.0

# Verify the node versions. Should print "v18.18.0".
node -v
```

- Install pnpm with version 10.5.0.

```
# Install pnpm
npm install pnpm@10.5.0 -g

# Verify the pnpm versions. Should print "v10.5.0"
pnpm -v
```

- Clone the repo to your local in VS Code terminal or others.

```
git clone https://github.com/twist-gaming/carrot-game-sdk.git
cd carrot-game-sdk
```

- Install dependencies.

```
pnpm install
```

- Run `pnpm run storybook --filter=<MODULE_NAME>` to storybook of a sample game in a turborepo way. `<MODULE_NAME>` is the name in the package.json file of a module in apps and packages folders. For example, we have `"name": "lines"` in the apps/lines/package.json, so we can find it and run its storybook by:

```
pnpm run storybook --filter=lines
```

- You should see this:

![](../fe_assets/storybook_init.png)
<!-- <img src="storybook_init.png" alt="isolated" width="100%"/> -->

###

- Now switch to MODE_BASE/book/random in the left sidebar, you will see an `Action` button appear on the left right conner of the game.

![](../fe_assets/storybook_action.png)
<!-- <img src="storybook_action.png" alt="isolated" width="100%"/> -->

###

- Click on the `Action` button and wait for a base game to finish.
- Congratulations! You are now in the zone of game development with us.

## Explore Storybook

Storybook is a powerful and handy tool to test your games. For example:

- `MODE_BASE/book/random`: It tests the <Game \/> component with a random book of base mode.
- `MODE_BASE/bookEvent/reveal`: It tests the <Game \/> component with a "reveal" bookEvent of the base mode. It will spin the reels.
- `MODE_BONUS/book/random`: It tests the <Game \/> component with a random book of bonus mode.
- `MODE_BONUS/bookEvent/reveal`: It tests the <Game \/> component with a "reveal" bookEvent of the bonus mode. It will spin the reels.
- ...
- `COMPONENTS/<GAME>/component`: It tests the <Game \/> component. In this case, it doesn't skip the loading screen.
- `COMPONENTS/<GAME>/preSpin`: It tests the <Game \/> component with the preSpin function.
- `COMPONENTS/<GAME>/emitterEvent`: It tests the <Game \/> component with an emitterEvent "boardHide".
- ...
- `COMPONENTS/<Symbol>/component`: It tests the <Symbol \/> component with controls e.g. state of the symbol.
- `COMPONENTS/<Symbol>/symbols`: It tests the <Symbol \/> component with all the symbols and all the states.

<img src="storybook_symbol.png" alt="isolated" width="100%"/>
<img src="storybook_symbols.png" alt="isolated" width="100%"/>

###

With all the above stories and the stories you create and customise by yourself, it is able to test the game as a whole, intermediate components or atomic components. It is also able to test your game with a book, a sequence of bookEvents or a single bookEvent. If each bookEvent is implemented well with emitterEvents and its story is resolved properly, the game is almost finished.

## Flow Chart

Here it is a simplified flow chart of steps how a game is processed after RGS request. The real situation might be more complicated, but it follows the same idea.

![](../fe_assets/flow_chart.png)
<!-- <img src="flow_chart.png" alt="isolated" width="100%"/> -->

- `playBookEvents()`: This is a function that's created by `createPlayBookUtils()` from `packages/utils-book`. What it does is to go through bookEvents one by one, handle each with async function (`playBookEvent()`) and resolve them one after another (`sequence()`) with the order of the bookEvents array.

  - That means the order of bookEvents matters and it determines the order of the game. For example, we don't wanna see the "win" before "spin", so we should put "win" after the "spin". This function is also used in the `MODE_XXX/book/random` stories.

  - `sequence()`: This is an in-house async function to achieve resolving async functions/promises one after another. On the contrast, `Promise.all()` will trigger all the async functions/promises together at the same time, which is not what we desire for the sequence of the game.

  - `playBookEvent()`: This is a function that takes in a bookEvent with some context (usually all the bookEvents), then find the bookEventHandler in bookEventHandlerMap based on `bookEvent.type` to process it. This function is also used in the `MODE_XXX/bookEvent/xxx` stories.

```
const playBookEvents = async (
  bookEvents: TBookEvent[],
  bookEventContext?: BookEventContextFromMapWithoutBookEvents,
) => {
  const finalBookEventContext =
    bookEventContext || ({} as BookEventContextFromMapWithoutBookEvents);

  await sequence(bookEvents, async (bookEvent) => {
    await playBookEvent(bookEvent, { ...finalBookEventContext, bookEvents });
  });
};
```

## BookEvent

- `Book`: A book is a json data that is returned from the RGS (Remote Game Server) for each game requested. It is randomly picked from over a million of books, which we call it [math](https://twist-gaming.github.io/carrot-math-engine).

```
// Example of a base game book
{
  id: 1,
  payoutMultiplier: 0.0,
  events: [
    {
      index: 0,
      type: 'reveal',
      board: [
        [{ name: 'L2' }, { name: 'L1' }, { name: 'L4' }, { name: 'H2' }, { name: 'L1' }],
        [{ name: 'H1' }, { name: 'L5' }, { name: 'L2' }, { name: 'H3' }, { name: 'L4' }],
        [{ name: 'L3' }, { name: 'L5' }, { name: 'L3' }, { name: 'H4' }, { name: 'L4' }],
        [{ name: 'H4' }, { name: 'H3' }, { name: 'L4' }, { name: 'L5' }, { name: 'L1' }],
        [{ name: 'H3' }, { name: 'L3' }, { name: 'L3' }, { name: 'H1' }, { name: 'H1' }],
      ],
      paddingPositions: [216, 205, 195, 16, 65],
      gameType: 'basegame',
      anticipation: [0, 0, 0, 0, 0],
    },
    { index: 1, type: 'setTotalWin', amount: 0 },
    { index: 2, type: 'finalWin', amount: 0 },
  ],
  criteria: '0',
  baseGameWins: 0.0,
  freeGameWins: 0.0,
}
```

- `BookEvent`: A bookEvent is a json data that is one of the element of the `book.events` array.

```
// Example of a "reveal" bookEvent
{
  index: 0,
  type: 'reveal',
  board: [
    [{ name: 'L2' }, { name: 'L1' }, { name: 'L4' }, { name: 'H2' }, { name: 'L1' }],
    [{ name: 'H1' }, { name: 'L5' }, { name: 'L2' }, { name: 'H3' }, { name: 'L4' }],
    [{ name: 'L3' }, { name: 'L5' }, { name: 'L3' }, { name: 'H4' }, { name: 'L4' }],
    [{ name: 'H4' }, { name: 'H3' }, { name: 'L4' }, { name: 'L5' }, { name: 'L1' }],
    [{ name: 'H3' }, { name: 'L3' }, { name: 'L3' }, { name: 'H1' }, { name: 'H1' }],
  ],
  paddingPositions: [216, 205, 195, 16, 65],
  gameType: 'basegame',
  anticipation: [0, 0, 0, 0, 0],
}

// Example of a setTotalWin bookEvent
{ index: 1, type: 'setTotalWin', amount: 0 },
```

- `BookEventHandler`: An async function that takes in a bookEvent and do some operations with it. Usually it broadcasts some emitterEvents, so the components will handle.

- `bookEventHandlerMap`: An object that the key is `bookEvent.type` and value is a bookEventHandler. We can find this big-boy object in `src/game/bookEventHandlerMap.ts`.

```
// Example of "updateFreeSpin" bookEventHandler
export const bookEventHandlerMap: BookEventHandlerMap<BookEvent, BookEventContext> = {
  ...,
  updateFreeSpin: async (bookEvent: BookEventOfType<'updateFreeSpin'>) => {
    stateApp.eventEmitter.next({ type: 'freeSpinCounterShow' });
    stateApp.eventEmitter.next({
      type: 'freeSpinCounterUpdate',
      current: bookEvent.amount,
      total: bookEvent.total,
    });
  },
  ...,
}
```

- In simple terms, a book is composed by multiple bookEvents. Different combinations of bookEvents will determine the different behaviours of a game e.g. win/lose, a big/small win, a base/bonus game, 1/10/15 spins and so on.

## EmitterEvent

- `EmitterEvent`: An emitterEvent is a json data that `stateApp.eventEmitter.next(emitterEvent)` or `stateApp.eventEmitter.asyncNext(emitterEvent)` broadcasts, so that a component which has `stateApp.eventEmitter.registerOnMount(emitterEventHandlerMap)` can receive the data and deal with it in a synchronous or asynchronous way. For a game we have many animations, so sometimes we need to "await" for those animations to finish before going to the next step.

```
// Example of an emitterEvent
{
  type: 'freeSpinCounterUpdate',
  current: undefined,
  total: bookEvent.totalFs,
}
```

- `EmitterEventHandler (Synchronous)`: A sync function that takes in an emitterEvent. It usually deal with some sync operations e.g. show/hide component, tidy up, update some numbers and so on.

```
// Example of broadcasting
stateApp.eventEmitter.next({
  type: 'freeSpinCounterUpdate',
  current: undefined,
  total: bookEvent.totalFs,
});

// Example of receiving
context.stateApp.eventEmitter.registerOnMount({
  // emitterEventHandlerMap
  ...,
  freeSpinCounterUpdate: (emitterEvent) => {
    if (emitterEvent.current !== undefined) current = emitterEvent.current;
    if (emitterEvent.total !== undefined) total = emitterEvent.total;
  },
  ...,
});
```

- `EmitterEventHandler (Asynchronous)`: An async function that takes in an emitterEvent. It usually deal with some async operations e.g. wait for fading in/out component, wait for animations to finish, wait for numbers to increase/decrease with [Tween](https://svelte.dev/docs/svelte/svelte-motion#Tween) and so on.

```
// Example of broadcasting
await stateApp.eventEmitter.asyncNext({
  type: 'freeSpinIntroUpdate',
  totalFreeSpins: bookEvent.totalFs,
});

// Example of receiving
context.stateApp.eventEmitter.registerOnMount({
  // emitterEventHandlerMap
  ...,
  freeSpinIntroUpdate: async (emitterEvent) => {
    freeSpinsFromEvent = emitterEvent.totalFreeSpins;
    await waitForResolve((resolve) => (oncomplete = resolve)); // Wait for an animation to finish.
  },
  ...,
});
```

- `emitterEventHandlerMap`: An object that the key is `emitterEvent.type` and value is an emitterEventHandler. We can find this object in each component. For example, `src/components/FreeSpinCounter.svelte`.
  - Each emitterEventHandler can do a lot or a little, but we prefer each emitterEventHandler just doing a minimum job to achieve the duty that's described by its name. This way we follow the single responsibility principle of [SOLID](https://www.digitalocean.com/community/conceptual-articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design#single-responsibility-principle). For example, `freeSpinCounterShow` just shows this component and does nothing more.

```
// Example of FreeSpinCounter.svelte and its emitterEventHandlers
<script lang="ts" module>
  export type FreeSpinCounterEmitterEvent =
    | { type: 'freeSpinCounterShow' }
    | { type: 'freeSpinCounterHide' }
    | { type: 'freeSpinCounterUpdate'; current?: number; total?: number };
</script>

<script lang="ts">
  ...

  context.stateApp.eventEmitter.registerOnMount({
    // emitterEventHandlerMap
    freeSpinCounterShow: () => (show = true),
    freeSpinCounterHide: () => (show = false),
    freeSpinCounterUpdate: (emitterEvent) => {
      if (emitterEvent.current !== undefined) current = emitterEvent.current;
      if (emitterEvent.total !== undefined) total = emitterEvent.total;
    },
  });
</script>

<MainContainer>
  ...
</MainContainer>
```

## Task Breakdown

- If an emitterEventHandler does too much work, then it's better we consider to split it into smaller emitterEventHandlers as a process of task-breakdown. For example, "tumbleBoard" bookEvent is a fairly complicated bookEvent. Instead of having one "tumbleBoard" emitterEvent, we split it into "tumbleBoardInit", "tumbleBoardExplode", "tumbleBoardRemoveExploded", "tumbleBoardSlideDown". This way we can implement a complicated emitterEvent step by step and more importantly, we can test the implementations one by one in storybook.

```
// Example of TumbleBoard.svelte and task-breakdown
context.stateApp.eventEmitter.registerOnMount({
  // emitterEventHandlerMap
  tumbleBoardShow: () => {},
  tumbleBoardHide: () => {},
  tumbleBoardInit: () => {},
  tumbleBoardReset: () => {},
  tumbleBoardExplode: () => {},
  tumbleBoardRemoveExploded: () => {},
  tumbleBoardSlideDown: () => {},
});
```

- Now it's easy to tell that, there's one single idea that's been applied across the whole carrot-game-sdk which is `Task Breakdown`. Stateless games can be complicated with different types of spins, number of spins, win rules, number of bookEvents, game modes, global multiplier, multiplier symbols and so on. However with the data structure of math and the in-house functions we have, we are able to break down a game into small tasks/emitterEvents as atomic pieces of code. It enables us to test the atomics independently as well. Visually it's something like this:

![](../fe_assets/task_breakdown.png)
<!-- <img src="task_breakdown.png" alt="isolated" width="100%"/> -->

## New BookEvent: Steps to Implement and Test

- `New BookEvent`: Assume that you have a game already and you have added a new bookEvent `updateGlobalMult` to the bonus game mode (`MODE_BONUS`) in math, here we will go through the steps together to implement the new bookEvent and add it to the game. Along the way we will introduce part of our file structure as well.

- `src/stories/data/bonus_books.ts`: This file includes the an array of bonus books that story `MODE_BONUS/book/random` will randomly pick at. This is to simulate requesting data from RGS. All we need to do is to copy/paste data from our new math package and format it.

```
// Example of "updateGlobalMult" bookEvent. That's been added in our `bonus_books.ts` during generating math.
{
  type: 'updateGlobalMult',
  globalMult: 3,
},
```

- `src/stories/data/bonus_events.ts`: This file includes the an object of every type of bookEvent that story `MODE_BONUS/bookEvent/xxx` uses. All we need to do is to copy/paste data from our new math package and format it.

```
export default {
  ...,
  updateGlobalMult: {
    type: 'updateGlobalMult',
    globalMult: 3,
  },
  ...,
}
```

- `src/stories/ModeBaseBookEvent.stories.svelte`: This file implements all the sub stories in story `MODE_BONUS/book/updateGlobalMult`. With the following code added in this file, you will see the a new story `MODE_BONUS/book/updateGlobalMult` that's added in our storybook with an `Action` button. Now if we click on it and nothing would happen, but it's a good start because we set up the testing environment first. Next step is to add code of bookEventHandler to handle it.

```
<Story
  name="updateGlobalMult"
  args={templateArgs({
    skipLoadingScreen: true,
    data: events.updateGlobalMult,
    action: async (data) => await playBookEvent(data, { bookEvents: [] }),
  })}
/>
```

- `src/game/typesBookEvent.ts`: This file contains typescript types of all the bookEvents. Let's add the type of our new bookEvent to get the intellisense from typescript for the following step.
  - `type BookEvent` is a union type.

```
type BookEventUpdateGlobalMult = {
  index: number;
  type: 'updateGlobalMult';
  globalMult: number;
};

export type BookEvent =
  | ...
  | BookEventUpdateGlobalMult
  | ...
;
```

- `src/game/bookEventHandlerMap.ts`: This file includes all the bookEventHandlers. Let's add a new one for the new bookEvent. Check the intellisense that the previous step brings, it provides a better developer experience.

![](../fe_assets/book_event_intellisense.png)
<!-- <img src="book_event_intellisense.png" alt="isolated" width="100%"/> -->

###

- `src/components/GlobalMultiplier.svelte`: This file is created as our target svelte component for updateGlobalMulti bookEvent. Technically speaking, all the jobs that's related to global multiplier of the game should only be in this svelte component. Similar to the bookEvent types, let's add the typescript types for new emitterEvents first.
  - `type GlobalMultiplierEmitterEvent` is a union type.

```
<script lang="ts" module>
  export type GlobalMultiplierEmitterEvent =
    | { type: 'globalMultiplierShow' }
    | { type: 'globalMultiplierHide' }
    | { type: 'globalMultiplierUpdate'; multiplier: number };
</script>
```

- `src/game/typesEmitterEvent.ts`: This file has typescript types of all the emitterEvents of the game. Let's add the type of our new emitterEvents for intellisense.
  - `type GameEmitterEvent` is a union type.

```
...
import type { GlobalMultiplierEmitterEvent } from '../components/GlobalMultiplier.svelte';
...

export type GameEmitterEvent =
  | ...
  | GlobalMultiplierEmitterEvent
  | ...
;
```

- `src/components/GlobalMultiplier.svelte`: Back to our component file, the intellisense is there. Let's add the code to process the values with a spine animation as well.

![](../fe_assets/emitter_event_intellisense.png)
<!-- <img src="emitter_event_intellisense.png" alt="isolated" width="100%"/> -->

###

```
<script lang="ts" module>
  export type GlobalMultiplierEmitterEvent =
    | { type: 'globalMultiplierShow' }
    | { type: 'globalMultiplierHide' }
    | { type: 'globalMultiplierUpdate'; multiplier: number };
</script>

<script lang="ts">
  ...

  context.stateApp.eventEmitter.registerOnMount({
    // emitterEventHandlerMap
    globalMultiplierShow: () => (show = true),
    globalMultiplierHide: () => (show = false),
    globalMultiplierUpdate: async (emitterEvent) => {
      console.log(emitterEvent.multiplier)
    },
  });
</script>

<SpineProvider key="globalMultiplier" width={PANEL_WIDTH}>
  ...
  <SpineTrack trackIndex={0} {animationName} />
</SpineProvider>
```

- `Test`: Run `pnpm run storybook --filter=<MODULE_NAME>` in the terminal. We should see this:

![](../fe_assets/storybook_add_new_book_event.png)
<!-- <img src="storybook_add_new_book_event.png" alt="isolated" width="100%"/> -->

###

- Now click on the `Action` button and we should see the `<GlobalMultiplier />` animates correctly followed by the "Action is resolved" message, otherwise we need to go back to the component and figure out what's wrong until it's resolved.

![](../fe_assets/storybook_action_resolved.png)
<!-- <img src="storybook_action_resolved.png" alt="isolated" width="200"/> -->

###

- If you find out the component hard to debug, we'd better start creating `COMPONENTS/<GlobalMultiplier>/component` or something even more lower level like `COMPONENTS/<GlobalMultiplierSpine>/component`. For which `<GlobalMultiplierSpine />` component takes props instead of being controlled by emitterEvents. It's more friendly to test the component with the storybook controls.

## To Be Continued
