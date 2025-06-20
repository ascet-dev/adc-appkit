# ADC AppKit

ADC AppKit is a lightweight component-based framework for applications. It provides a clean and intuitive way to manage application components, their dependencies, and lifecycle events.

## Features

- Component-based architecture for better code organization
- Automatic dependency injection
- Lifecycle management for application components
- Easy integration with any framework
- Type-safe component configuration

## Installation

```bash
pip install adc-appkit
```

## Quick Start

```python
from adc_appkit import Component, App

class MyComponent(Component):
    async def startup(self):
        # Initialize your component
        pass

    async def shutdown(self):
        # Cleanup resources
        pass

appkit = App()

@appkit.component
async def my_component():
    return MyComponent()

# Your application logic here
```

## Documentation

For more information, please visit our [documentation](https://github.com/ascet-dev/adc-appkit).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
