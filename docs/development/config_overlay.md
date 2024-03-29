# AMP Configuration Overlay

AMP is configured with a set of YAML files which are combined to
create a single data structure which is shared across all components.

When an AMP package is constructed, it has the ability to define a
user defaults file (for options that are likely to be modified by the the
end user), a system defaults file (which is unlikely to be changed by the
user), and a script that will hook into when the system is being reconfigured.

This design was chosen for several reasons:
* Different components may be installed at each site, so a unified
  configuration would be hard to maintain
* Third party MGMs and other tools may need full access to the configuration
* There are a lot of cross-dependencies between different components
* different components have different configuration file formats
* some configuration is likely to be modified by the end user and others
  are mostly constrained to the developers.

When AMP is being reconfigured by the `./amp_config.py configure` command,
the different YAML fragments are gathered from around the installation and
combined.  The merge order is:
* amp_bootstrap/amp.default
* data/default_configs/*.{system,user}_defaults  (these were all installed as 
  part of the packages)
* data/package_config/*.yaml  (these are run-time configuration values)
* amp_bootstrap/amp.yaml  (the user configuration)

The rules for merging are fairly straightforward.  Given a model dictionary
and an overlay dictionary, for each of the overlay keys:
* If the key doesn't exist in the model, the overlay key and value are inserted
* If the key exists in the model:
  * If the value is a dict, the merger function will recurse at that point in 
    the tree
  * Otherwise, the model's value is replaced with the overlay's value.

## data/package_config
The yaml files in the data/package_config directory are generated by the
different configuration hook scripts to pass information to other parts of
the configuration or to store persistent auto-generated values.

The different secret values are handled using this mechanism.

## User vs System defaults
A default value should be put into the user_defaults if it is anticipated that
the configuration value will be modified by the end user.  Things like ports,
help links, database config, cloud credentials, etc. are good candidates for 
this.

The system defaults are used for configuration that the user isn't expected to
modify except in extreme circumstances -- springboot settings, etc.



