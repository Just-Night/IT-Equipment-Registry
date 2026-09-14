from drf_yasg.generators import OpenAPISchemaGenerator


class TaggedSchemaGenerator(OpenAPISchemaGenerator):
    def get_paths(self, endpoints, components, request, public):
        # Викликаємо базовий метод для отримання шляхів
        paths = super().get_paths(endpoints, components, request, public)

        # Перевіряємо кожен endpoint
        for endpoint, (path_item, path) in endpoints.items():
            # Перевіряємо, чи маршрут містить ключове слово 'guilds'
            if 'guilds' in endpoint[0]:
                for method in path_item.operations:
                    path_item.operations[method]["tags"] = ["discord_guilds"]
            # Можна додати більше правил для інших тегів тут

        return paths
