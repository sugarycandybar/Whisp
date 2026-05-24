conf_data = configuration_data()
conf_data.set('bindir', join_paths(get_option('prefix'), get_option('bindir')))

configure_file(
  input: 'com.example.Whisp.desktop.in',
  output: 'com.example.Whisp.desktop',
  configuration: conf_data,
  install: true,
  install_dir: get_option('datadir') / 'applications'
)


install_data('com.example.Whisp.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo'
)

install_data('icons/hicolor/scalable/apps/com.example.Whisp.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps'
)
