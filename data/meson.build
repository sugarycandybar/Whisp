conf_data = configuration_data()
conf_data.set('bindir', join_paths(get_option('prefix'), get_option('bindir')))

configure_file(
  input: 'io.github.tanaybhomia.Whisp.desktop.in',
  output: 'io.github.tanaybhomia.Whisp.desktop',
  configuration: conf_data,
  install: true,
  install_dir: get_option('datadir') / 'applications'
)


install_data('io.github.tanaybhomia.Whisp.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo'
)

install_data('icons/io.github.tanaybhomia.Whisp.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps'
)

install_data('icons/io.github.tanaybhomia.Whisp-symbolic.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/symbolic/apps'
)

install_data('icons/io.github.tanaybhomia.Whisp-pin-symbolic.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/symbolic/apps'
)

# D-Bus service files (D-Bus activation for the app and its search provider)
configure_file(
  input: 'io.github.tanaybhomia.Whisp.service.in',
  output: 'io.github.tanaybhomia.Whisp.service',
  configuration: conf_data,
  install: true,
  install_dir: get_option('datadir') / 'dbus-1' / 'services'
)

configure_file(
  input: 'io.github.tanaybhomia.Whisp.SearchProvider.service.in',
  output: 'io.github.tanaybhomia.Whisp.SearchProvider.service',
  configuration: conf_data,
  install: true,
  install_dir: get_option('datadir') / 'dbus-1' / 'services'
)

# GNOME Shell search provider registration
install_data('io.github.tanaybhomia.Whisp-search-provider.ini',
  install_dir: get_option('datadir') / 'gnome-shell' / 'search-providers'
)

# Desktop file validation
desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [join_paths(meson.current_build_dir(), 'io.github.tanaybhomia.Whisp.desktop')]
  )
endif

# Appstream validation
appstream_utils = find_program('appstreamcli', required: false)
if appstream_utils.found()
  test('Validate appstream file', appstream_utils,
    args: ['validate', '--no-net', '--explain', join_paths(meson.current_source_dir(), 'io.github.tanaybhomia.Whisp.metainfo.xml')]
  )
endif
