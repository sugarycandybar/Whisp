python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())

configure_file(
  input: 'nota.in',
  output: 'nota',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)
