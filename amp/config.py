"Utility functions for configuration management"


import logging



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
