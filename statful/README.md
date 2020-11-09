# Statful client

An Statful client plugin, sending various data to Statful.

## Configuration

```
config_description = [{'name': 'token',
                       'type': 'str',
                       'description': 'Statful API token for authentication.'},
                      {'name': 'add_custom_tag',
                       'type': 'str',
                       'description': 'Add custom tag to statistics'},
                      {'name': 'batch_size',
                       'type': 'int',
                       'description': 'The maximum batch size of grouped metrics to be send to Statful.'}]
```

The ```token``` parameter is self-explaining. The ```custom_tag``` parameter allows to push a tag key `custom_tag` with a user-input value.
The ```batch_size``` parameter defines the maximum size of metrics on a batch. 

## Data

All data is send using the [Metrics Ingestion Protocol](https://www.statful.com/docs/metrics-ingestion-protocol.html#Metrics-Ingestion-Protocol):

### Outputs

This plugin sends all data that is available on the Gateway metrics bus to Statful.
