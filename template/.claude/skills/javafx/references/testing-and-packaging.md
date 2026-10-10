# JavaFX: testing and packaging

Part of the `javafx` skill. Everything here that adds a dependency or a plugin goes
through the company mirror: check the POM first, take versions from the mirror, and ask
before adding anything or running a build that downloads.

## TestFX with JUnit 5

TestFX starts a real JavaFX stage and drives it like a user. Use it only if the POM
already has `org.testfx` (or after the person agrees to add it); logic in view models or
interactors is tested with plain JUnit, no screen needed.

- Dependencies (test scope): `org.testfx:testfx-junit5`, plus `org.testfx:testfx-core`
  if the project does not get it transitively. For assertions, use the project's
  AssertJ if it has one, or TestFX's own matchers.
- Mark the class with `@ExtendWith(ApplicationExtension.class)`. A method marked `@Start`
  builds the stage before each test; an `FxRobot` parameter clicks and types.

```java
@ExtendWith(ApplicationExtension.class)
class LoginViewTest {

    @Start
    void start(Stage stage) throws IOException {
        Parent root = FXMLLoader.load(getClass().getResource("/app/login.fxml"));
        stage.setScene(new Scene(root));
        stage.show();
    }

    @Test
    void empty_password_disables_login(FxRobot robot) {
        robot.clickOn("#user").write("ana");
        assertThat(robot.lookup("#login").queryButton().isDisabled()).isTrue();
    }
}
```

- Look nodes up by `fx:id` (`#login`) or style class, not by visible text that may be
  translated.
- After an action that starts a `Task`, wait for it
  (`WaitForAsyncUtils.waitForFxEvents()`, or wait until a condition holds); never use
  `Thread.sleep`.
- Keep UI tests few and focused on wiring (does the button reach the view model?); put
  the rules in faster unit tests.

## Headless on an Ubuntu CI: Monocle

A CI agent has no display. Monocle is a JavaFX platform that renders off screen, so
TestFX runs headless.

1. Add the Monocle artifact in test scope, through the mirror:
   `org.testfx:openjfx-monocle`, in the version line that matches the project's JavaFX
   major (for example a 21.x Monocle for JavaFX 21). Ask before adding it.
2. Pass these system properties to the test JVM, usually in the Surefire
   `<argLine>` or a Maven profile used only on CI:

   ```text
   -Dtestfx.robot=glass -Dtestfx.headless=true -Dprism.order=sw -Dglass.platform=Monocle -Dmonocle.platform=Headless
   ```

3. Run the tests as usual (after a yes, since a first build may download).

If Monocle cannot be added, the fallback is a virtual display (`xvfb-run mvn test`), but
only if the CI image already has Xvfb; installing packages on the agent is the CI team's
decision. With a module path build, Monocle may also need `--add-exports` lines; copy
the exact error into your report rather than guessing.

## javafx-maven-plugin

`org.openjfx:javafx-maven-plugin` runs and links a JavaFX app from Maven. Use the
version the POM has; configure `<mainClass>` (with the module name for a modular app:
`app/com.example.App`).

- `mvn javafx:run` starts the app with the right module path.
- `mvn javafx:jlink` builds a runtime image of the app (see below). It needs a modular
  app (`module-info.java`) whose dependencies are modules too.

Ask before running either: the first run may download plugins through the mirror.

## jlink and jpackage

- **`jlink`** makes a **runtime image**: a folder with a trimmed Java runtime holding only
  the modules the app needs, plus the app. It runs on the same OS and CPU it was built
  for. It needs a modular app, or a list of modules given by hand.
- **`jpackage`** makes an **installer or app bundle** for one platform: `.deb` or `.rpm`
  on Linux, `.msi` or `.exe` on Windows, `.dmg` or `.pkg` on macOS. It builds only for the
  platform it runs on, and it needs that platform's tools (on Ubuntu, `dpkg-deb` for a
  `.deb`, `rpmbuild` for an `.rpm`; on Windows, the WiX toolset). Check they are present;
  do not install them yourself.

Before running `jpackage`, tell the person what it will make, where, and with which
options (name, version, icon, main class, runtime image), and wait for a yes. Signing an
installer uses company certificates: the person or the release team does that.

## With a Zulu FX JDK

When JavaFX comes from the JDK (an Azul Zulu "JDK FX" build):

- Do not add `org.openjfx` dependencies, and do not add the `javafx-maven-plugin` just to
  get JavaFX on the module path: the JDK already has the JavaFX modules.
- `jlink` and `jpackage` from that JDK can include the JavaFX modules like any other
  JDK module (`--add-modules javafx.controls,javafx.fxml`).
- CI and every developer must use the same FX JDK. If the build fails with
  "module javafx.controls not found", the JDK in use is not the FX build: report which
  `java -version` ran.
