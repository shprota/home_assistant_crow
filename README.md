# home_assistant_crow
Home Assistant Crow Cloud integration
## Usage
- Clone to custom_components in your Home Assistant config dir.
- Add the following to configuration.yaml
```yaml
crow:
  username: !secret crow_username
  password: !secret crow_password
  panel_mac: !secret crow_mac # Crow Panel MAC  
```
