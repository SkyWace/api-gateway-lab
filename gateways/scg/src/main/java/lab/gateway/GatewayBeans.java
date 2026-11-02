package lab.gateway;

import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Configuration
public class GatewayBeans {

    /** Clé de quota = en-tête X-Client-Id (même critère que Kong, APISIX et Traefik). */
    @Bean
    KeyResolver clientKeyResolver() {
        return exchange -> Mono.just(Optional
                .ofNullable(exchange.getRequest().getHeaders().getFirst("X-Client-Id"))
                .orElse("anonymous"));
    }

    /** Corrélation : génère X-Request-ID s'il est absent, le propage au backend et le renvoie au client. */
    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE)
    GlobalFilter requestIdFilter() {
        return (exchange, chain) -> {
            String id = Optional.ofNullable(exchange.getRequest().getHeaders().getFirst("X-Request-ID"))
                    .orElse(UUID.randomUUID().toString());
            var mutated = exchange.mutate()
                    .request(r -> r.headers(h -> h.set("X-Request-ID", id)))
                    .build();
            mutated.getResponse().getHeaders().set("X-Request-ID", id);
            return chain.filter(mutated);
        };
    }

    /** Réponse de repli quand le circuit breaker "orders" est ouvert. */
    @RestController
    static class FallbackController {
        @RequestMapping("/fallback/orders")
        Mono<ResponseEntity<Map<String, String>>> ordersFallback() {
            return Mono.just(ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("error", "circuit_open")));
        }
    }
}
