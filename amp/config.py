"Utility functions for configuration management"


import logging
import os
import yaml
from pathlib import Path


def load_amp_config(amp_root=None):
    """
    Load the AMP configuration, applying all of the overlays as needed
    """
    if amp_root is None:
        if 'AMP_ROOT' in os.environ:
            amp_root = os.environ['AMP_ROOT']
        else:
            raise IOError("Cannot figure out where the AMP_ROOT is!")

    # the base file for all overlays is in amp_bootstrap/amp.default  
    default_file = Path(amp_root, 'amp_bootstrap/amp.default')
    if not default_file.exists():
        raise FileNotFoundError(f"Cannot load the amp.default file!  Expected it at {default_file!s}")    
    with open(default_file) as f:
        config = yaml.safe_load(f)

    logging.debug(f"Base default config: {config}")


    # other packages may have left default files in the data/default_config directory -- let's find them and
    # overlay them on the primary default file.
    for default in Path(amp_root, "data/default_config").glob("*.default"):
        try:
            with open(default) as f:
                overlay = yaml.safe_load(f)
            _merge(config, overlay)
            logging.debug(f"Default config after merging with {default!s}: {config}")
        except Exception as e:
            logging.warning(f"Cannot overlay {default!s}: {e}")


    # At this point we should have a full default configuration -- overlay the
    # user configuration
    try: 
        with open(Path(amp_root, "amp_bootstrap/amp.yaml")) as f:
            overlay = yaml.safe_load(f)
        _merge(config, overlay)
        logging.debug(f"Default config after merging with user config: {config}")
    except Exception as e:
        raise IOError(f"Cannot overlay main configuration: {e}")

    return config

def _merge(model, overlay, context=None):
    "Merge two dicts"
    if not context:
        context = []
        
    def context_string():
        return '.'.join(context)

    logging.debug(f"Merge context: {context_string()}")
    for k in overlay:
        if k not in model:
            logging.warning(f"Adding un-modeled value: {context_string()}.{k} = {overlay[k]}")
            model[k] = overlay[k]
        elif type(overlay[k]) is not type(model[k]):            
            if type(overlay[k]) is type(None):
                logging.debug(f"Removing {context_string()}.{k}")
                model.pop(k)
            else:
                logging.warning(f"Skipping - type mismatch: {context_string()}.{k}:  model={type(model[k])}, overlay={type(overlay[k])}")
        elif type(overlay[k]) is dict:   
            nc = list(context)
            nc.append(k)         
            _merge(model[k], overlay[k], nc)
        else:
            # everything else is replaced wholesale
            logging.debug(f"Replacing value: {context_string()}.{k}:  {model[k]} -> {overlay[k]}")
            model[k] = overlay[k]

def get_config_value(config, keylist, default=None):
    "Walk the config using the keylist, returning the default if something goes wrong"
    if len(keylist) == 0:
        return config
    thiskey = keylist.pop(0)
    if thiskey in config:
        return get_config_value(config[thiskey], keylist, default)
    else:
        return default

