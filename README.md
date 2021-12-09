# ndbproxy [![version](https://img.shields.io/github/v/tag/b0o/ndbproxy?style=flat&color=yellow&label=version&sort=semver)](https://github.com/b0o/ndbproxy/releases) [![license: MIT](https://img.shields.io/github/license/b0o/ndbproxy?style=flat&color=green)](https://mit-license.org)

A proxy/bridge that runs between a Node.JS debug server and a Chromium devtools client and adds some additional features. 

- A stable URL, no need for a debugger ID, e.g. `devtools://devtools/bundled/js_app.html?v8only=true&ws=localhost:9228`
- Auto-reconnect to the debug server when it restarts
- Auto-reload the devtools debugger when the server restarts
- Optional [mitmproxy](https://github.com/mitmproxy/mitmproxy) integration

### Usage

1. Start ndbproxy: `python ndbproxy.py`

   - Note: ndbproxy listens on `localhost:9228`. Currently this address cannot be configured.

2. start the debug server: `node --inspect-brk app.js`

   - Note: ndbproxy expects the debug server to be available at `localhost:9229`. Currently this address cannot be configured.

3. Open the Chromium debugger at `devtools://devtools/bundled/js_app.html?v8only=true&ws=localhost:9228`

### Why?

I find it very annoying that there's no way to launch the Chrome/Chromium
Node.js debugger directly from the command line. I also find it annoying that
it's necessary to specify the debugger ID in the URL and that this ID changes
each time the node debug server restarts. Finally, I find it annoying that the
debugger doesn't automatically reconnect to the debug server when the server
restarts. ndbproxy solves all of these annoyances.

### Tips

#### Chromium profile & shell alias

For added convenience, I recommend you take a few steps to make launching the Chromium devtools as easy as running a simple command.

Unfortunately, Chromium doesn't allow you to open a `chrome://` or
`devtools://` URL from its CLI. As a workaround, you can create a new Chromium
profile specifically for use with ndbproxy and set the homepage to the ndbproxy
URL. Then, whenever you start Chromium with this profile, it will open directly
to an instance of the Devtools pointed at the ndbproxy server.

Finally, create a shell alias to launch Chromium with this profile: `alias node-devtools="chromium --user-data-dir=$XDG_CONFIG_HOME/chromium-node-inspect"`,
where `chromium-node-inspect` is the name of the profile.

#### Auto-reloading improvements

If your node app crashes or exits, you may want it to automatically start back up. Use a shell loop to accomplish this:

```sh
while :; do node --inspect-brk app.js; done
```

Adding to this, to automatically restart your node app when your code changes:

```sh
find . -not '(' -path ./node_modules -prune ')' -name '*.js' | entr -rds 'while :; do node --inspect-brk app.js; done'
```

```

```

## TODO

- [ ] allow `ndbproxy` to be used as a wrapper for the `node --inspect-brk` command
- [ ] add command-line arguments to configure listen/serve host:port
- [ ] reduce verbosity by default, add a `-v` flag
- [ ] extract mitmproxy integration to a separate file

## Changelog

```
08 Dec 2021                                                             v0.0.1
  Initial Release
```

## License

&copy; 2021 Maddison Hellstrom

Released under the MIT License.
