---
name: javafx
description: 'JavaFX desktop UI: the FX application thread, Task and Service, FXML and controllers, CSS, properties and bindings, listener leaks, MVVM or MVCI, TestFX tests (headless with Monocle), javafx-maven-plugin, jlink and jpackage. Use when the code imports javafx, has .fxml files, or the person says "JavaFX", "FXML", "the UI freezes", "TestFX", "jpackage".'
license: MIT
---

# JavaFX desktop UI

Help with JavaFX desktop apps on Java 17 and 21: keep the UI responsive, wire FXML
and controllers cleanly, avoid memory leaks, and test and package the app. Testing and
packaging details are in [references/testing-and-packaging.md](references/testing-and-packaging.md).

## Rules

- **Git:** never commit, push or merge on your own. Follow the person's git-comfort setting and ask before each commit.
- **Show before you change:** before editing or creating any file (a new test file too), show the proposed diff or content and wait for a yes; if you can't ask, stop after proposing. Report evidence (the test output), never just "Fixed".
- **Packages only through the company mirror:** never add `<repositories>` to a POM, never use `@latest`, and never run `npx` or `go install` against the public internet. Ask before anything that downloads. Load `ai-sdlc-maven-via-artifactory` (if you have it) to find the mirror and the versions this repo uses.
- **Follow the repo:** keep the pattern, layout style (FXML or code) and libraries the app already uses. Suggest a change of pattern; never make one unasked.

## 1. Where JavaFX comes from

JavaFX is not part of a plain JDK. A project gets it in one of two ways, and you must
know which before you add a module, a plugin or a test library:

- **`org.openjfx` dependencies** in the POM (`javafx-controls`, `javafx-fxml`, ...),
  one per module, all with the same version, usually from a `javafx.version` property.
- **A JDK that bundles JavaFX**, such as an Azul Zulu "JDK FX" build. Then the POM has no
  `org.openjfx` dependencies; the JDK is named in `.sdkmanrc`, `.java-version` or
  `.tool-versions` (for example `21.0.5.fx-zulu`), or only the `javafx` imports show it.

To find out, run the detector from `ai-sdlc-maven-via-artifactory` (if you have it) and
read `java.javafx`: `source` is `openjfx`, `jdk` or `unknown`, with a `version` and the
`evidence`. Without it, read the POM and the JDK files yourself. If the source is
`unknown`, ask the person which JDK they run.

- **Never mix the two.** With a Zulu FX JDK, do not add `org.openjfx` dependencies; with
  `org.openjfx`, do not assume the JDK has JavaFX.
- **Match the versions.** Keep the JavaFX major the project uses. JavaFX 17 and 21 run
  on Java 17; JavaFX 22 and later need Java 21. Every `org.openjfx` module gets the same
  version, from the mirror.

## 2. The FX application thread

JavaFX draws the screen and handles every event on one thread, the JavaFX Application
Thread. "The UI freezes" almost always means work is running on it.

- **Never block it.** No file or network access, database calls, `Thread.sleep` or long
  loops in an event handler, `initialize()` or a listener.
- **Never touch nodes from another thread.** A node in a live scene is changed only on
  the FX thread. Off it, hand the change over with `Platform.runLater(...)`.
- **Long work goes into a `Task`** (one run) or a **`Service`** (a reusable worker that
  creates a new `Task` each time it is started or restarted).

```java
Task<List<Order>> load = new Task<>() {
    @Override protected List<Order> call() throws Exception {
        updateMessage("Loading orders");
        return orderRepository.findOpen();          // runs on a worker thread
    }
};
load.setOnSucceeded(e -> table.getItems().setAll(load.getValue()));   // FX thread
load.setOnFailed(e -> showError(load.getException()));                // FX thread
statusLabel.textProperty().bind(load.messageProperty());
executor.submit(load);
```

- Report progress with `updateProgress` and `updateMessage` and bind to the task's
  properties. They are safe to call from `call()` and do not flood the FX thread the way
  many `Platform.runLater` calls in a loop do.
- Handle failure in `setOnFailed` (or the `exception` property). An exception inside
  `call()` is otherwise silent.
- Run workers on an executor with daemon threads, so the app can exit, and cancel running
  tasks when their view closes (`task.cancel()`; check `isCancelled()` in long loops).
- `Platform.runLater` is for a short hand-over, not a place for slow work: what it runs
  also runs on the FX thread.

## 3. FXML, controllers and CSS

- **The FXML names its controller** with `fx:controller="com.example.OrderController"`.
  Each `fx:id` maps to an `@FXML` field of the same name and type in the controller;
  handlers are referenced as `onAction="#save"`.
- **`initialize()` runs after the `@FXML` fields are injected.** Set up bindings and
  listeners there, not in the constructor (the fields are still `null` then).
- **No logic in FXML.** Layout and `fx:id`s only; no script blocks. Behaviour belongs in
  the controller or view model.
- **Dependencies into controllers** through `FXMLLoader.setControllerFactory(...)`, not
  through static fields. Follow the repo's way if it has one (Spring, Guice, a factory).
- **Style in CSS files** in the resources, added with
  `scene.getStylesheets().add(getClass().getResource("app.css").toExternalForm())`.
  Use style classes (`getStyleClass().add("danger")`) and `-fx-` properties; avoid
  inline `setStyle(...)` except for values computed at runtime.
- Load resources with `getClass().getResource(...)` relative to the class, and check the
  path when an FXML or CSS "is not found" (it must be on the classpath, under
  `src/main/resources`, in the same package folder).

## 4. Properties, bindings and listener leaks

- **Bind instead of copying.** `label.textProperty().bind(model.nameProperty())` keeps
  them in step; a copy goes stale. Use `bindBidirectional` for an editable field and its
  model value. A bound property cannot be set directly: unbind first.
- Derived values come from `Bindings` (`Bindings.createStringBinding`,
  `Bindings.when(...)`) or `property.map(...)` (JavaFX 19 and later), not from a listener
  that sets another property.
- **Listeners are for side effects** (save, log, start a task), not for passing data
  from one property to another.
- **Leaks:** a listener added to a long-lived object (a shared model, a service, a
  static) keeps the view that added it alive after the window closes. Either:
  - remove it when the view closes (for example in `stage.setOnHidden(...)`), and
    `unbind()` / `unbindBidirectional(...)` there too; or
  - wrap it in a `WeakChangeListener` (or `WeakInvalidationListener`, `WeakListChangeListener`),
    and keep a strong reference to the wrapped listener in a field of the view. Without
    that field the listener can be collected at once and simply stop firing.
- Anonymous classes and lambdas that use the view's fields hold the view too. Static
  fields that hold nodes, stages or controllers are a leak; flag them in review.

## 5. MVVM or MVCI

Both keep the UI thin and the logic testable without a screen. Follow what the repo uses.
For a new screen in a repo without a pattern, propose one and let the person choose:

- **MVVM** (Model, View, ViewModel): the view model exposes properties and actions; the
  view (FXML plus a small controller) only binds to them. A natural fit for FXML, and for
  teams that know MVVM from other UI stacks.
- **MVCI** (Model, View, Controller, Interactor): the model is a plain class of
  properties, the view builds the layout in code and binds to the model, the controller
  creates both and runs background tasks, and the interactor holds the business logic and
  talks to services. A good fit for layouts built in Java code.

In both, nothing in the model or logic layer imports `javafx.scene`; properties
(`javafx.beans`) are fine. That keeps the logic testable with plain JUnit.

## 6. Testing and packaging

Read [references/testing-and-packaging.md](references/testing-and-packaging.md) for:
TestFX with JUnit 5, running UI tests headless on an Ubuntu CI with Monocle, the
`javafx-maven-plugin` (`javafx:run`, `javafx:jlink`), and what `jlink` and `jpackage`
make. Ask before any build that downloads, and before running `jpackage`.

## Reviewing JavaFX code: quick checks

- Work on the FX thread that may block (I/O, sleeps, loops)?
- Nodes changed from a worker thread without `Platform.runLater` or `Task` events?
- `Task` failures handled? Tasks cancelled when the view closes?
- Listeners on long-lived objects removed or weak (with a strong field)?
- Logic in FXML, or `@FXML` fields used in a constructor?
- Inline styles that belong in CSS?
- `org.openjfx` modules all on one version, and not mixed with an FX JDK?
