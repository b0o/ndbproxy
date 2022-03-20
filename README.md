# ndbproxy [![version](https://img.shields.io/github/v/tag/b0o/ndbproxy?style=flat&color=yellow&label=version&sort=semver)](https://github.com/b0o/ndbproxy/releases) [![license: MIT](https://img.shields.io/github/license/b0o/ndbproxy?style=flat&color=green)](https://mit-license.org)

A websocket proxy that sits inbetween a Node.JS debug server and a Chromium devtools client for the purpose of adding some additional features:

- A stable URL, no need for a debugger ID, e.g. `devtools://devtools/bundled/js_app.html?v8only=true&ws=localhost:9228`
- Auto-reconnect to the debug server when it restarts
- Auto-reload the devtools debugger when the server restarts
- Optional [mitmproxy](https://github.com/mitmproxy/mitmproxy) integration

### Usage

1. Start ndbproxy: `python ndbproxy.py`

   - Note: ndbproxy listens on `localhost:9228`. Currently this address cannot be configured.

2. Run your node app with the `--inspect` or `--inspect-brk` flag: `node --inspect-brk app.js`

   - Note: ndbproxy expects the debug server to be available at `localhost:9229`. Currently this address cannot be configured.

3. Open the Chromium devtools at `devtools://devtools/bundled/js_app.html?v8only=true&ws=localhost:9228`

### Why?

I find it very annoying that Chromium provides no way to open the Node.js debugger directly from the command line. I also find it annoying that
it's necessary to specify the debugger ID in the URL and that this ID changes
each time the node debug server restarts. Finally, I find it annoying that the
debugger doesn't automatically reconnect to the debug server when the server
restarts. ndbproxy solves all of these annoyances.

### Tips

#### Chromium profile & shell alias

For added convenience, I recommend taking a few steps to make launching the Chromium devtools as simple as running a single command.

Unfortunately, Chromium doesn't permit opening a `chrome://` or
`devtools://` URL from the command line. As a workaround, create a new Chromium
profile specifically for use with ndbproxy and set the homepage to the ndbproxy
URL. Whenever Chromium is launched with this profile, it will open directly
to a devtools instance pointed at the ndbproxy server.

Then, create a shell alias to launch Chromium with this profile: `alias node-devtools="chromium --user-data-dir=$XDG_CONFIG_HOME/chromium-node-inspect"`,
where `chromium-node-inspect` is the name of the profile.

#### Auto-reloading improvements

If your node application crashes or exits, you may want it to restart automatically. Use a shell loop to accomplish this:

```sh
while :; do node --inspect-brk app.js; done
```

To automatically restart your node app and reload the debugger when your code changes:

```sh
find . -not '(' -path ./node_modules -prune ')' -name '*.js' | entr -rds 'while :; do node --inspect-brk app.js; done'
```

## TODO

- [ ] allow `ndbproxy` to be used as a wrapper for the `node --inspect-brk` command
- [ ] add command-line arguments to configure listen/serve host:port
- [ ] reduce verbosity by default, add a `-v` flag
- [ ] extract mitmproxy integration to a separate file
- [ ] come up with a better name
- [ ] detect and prevent reload loops
- [ ] detect `Waiting for debugger to disconnect`

## Changelog

```
08 Dec 2021                                                             v0.0.1
  Initial Release
```

## License

&copy; 2021 Maddison Hellstrom

Released under the MIT License.
